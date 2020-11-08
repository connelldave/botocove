import asyncio
import functools
import logging
from concurrent import futures
from functools import partial
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.config import Config

from botocove.cove_session import CoveSession

logger = logging.getLogger(__name__)

DEFAULT_ROLENAME = "OrganizationAccountAccessRole"

config = Config(max_pool_connections=20)


def _get_cove_session(org_client, sts_client, account_id, rolename) -> CoveSession:
    role_arn = f"arn:aws:iam::{account_id}:role/{rolename}"
    account_details = org_client.describe_account(AccountId=account_id)["Account"]
    cove_session = CoveSession(account_details)
    try:
        logger.debug(f"Attempting to assume {role_arn}")
        creds = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=rolename)[
            "Credentials"
        ]
        cove_session.initialize_boto_session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )
    except Exception as e:
        cove_session.store_exception(e)

    return cove_session


def _get_org_accounts(
    org_client, sts_client, ignore_ids: Optional[List[str]]
) -> Set[str]:
    calling_account = set(sts_client.get_caller_identity()["Account"])
    accounts_to_ignore = set(calling_account)

    if ignore_ids:
        accounts_to_ignore = set(ignore_ids) | accounts_to_ignore

    all_org_accounts = (
        org_client.get_paginator("list_accounts")
        .paginate()
        .build_full_result()["Accounts"]
    )

    active_accounts = {
        acc["Id"] for acc in all_org_accounts if acc["Status"] == "ACTIVE"
    }

    target_accounts = active_accounts - accounts_to_ignore
    return target_accounts


async def _get_account_sessions(org_client, sts_client, rolename, accounts):
    with futures.ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                _get_cove_session,
                org_client,
                sts_client,
                account_id,
                rolename,
            )
            for account_id in accounts
        ]
    sessions = await asyncio.gather(*tasks)
    return sessions


def wrap_func(func, raise_exception, account_session, *args, **kwargs):
    # A simple wrapper to handle capturing and working with decorated func exceptions
    try:
        result = func(account_session, *args, **kwargs)
        return account_session.format_cove_result(result)
    except Exception as e:
        if raise_exception is True:
            account_session.store_exception(e)
            logger.exception(account_session.format_cove_error())
            raise
        else:
            account_session.store_exception(e)
            return account_session.format_cove_error()


async def _async_boto3_call(valid_sessions, raise_exception, func, *args, **kwargs):
    with futures.ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                partial(
                    wrap_func, func, raise_exception, account_session, *args, **kwargs
                ),
            )
            for account_session in valid_sessions
        ]

    completed = await asyncio.gather(*tasks)
    successful_results = [
        result for result in completed if not result.get("ExceptionDetails")
    ]
    exceptions = [result for result in completed if result.get("ExceptionDetails")]
    return successful_results, exceptions


def cove(
    _func=None,
    *,
    target_ids=None,
    ignore_ids=None,
    rolename=None,
    org_session=None,
    raise_exception=False,
):
    def decorator(func):
        @functools.wraps(func)
        # TODO return a dict of CoveSession?
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # If undefined, use credentials from boto3 credential chain
            if not org_session:
                logger.info("No Boto3 session argument: using credential chain")
                sts_client = boto3.client("sts", config=config)
                org_client = boto3.client("organizations", config=config)
            # Use boto3 session supplied as arg
            else:
                logger.info(
                    f"Boto3 session {org_session} argument provided: using to create "
                )
                sts_client = org_session.client("sts")
                org_client = org_session.client("organizations")

            # Create a set of account ID's to run function against
            if not target_ids:
                account_ids = _get_org_accounts(org_client, sts_client, ignore_ids)
            elif ignore_ids:
                account_ids = set(target_ids) - set(ignore_ids)
            else:
                account_ids = set(target_ids)

            if not account_ids:
                raise ValueError(
                    "There are no eligible account ids to run decorated func "
                    f"{func.__name__} against"
                )
            # Role to assume in each account
            if not rolename:
                # If undefined, use default AWS organization role
                role_to_assume = DEFAULT_ROLENAME
            else:
                # Use supplied role name
                role_to_assume = rolename

            logger.info(
                f"Running func {func.__name__} against accounts passing arguments: "
                f"{role_to_assume=} {target_ids=} {ignore_ids=} {org_session=}"
            )
            logger.debug(f"accounts targeted are {account_ids}")

            sessions = asyncio.run(
                _get_account_sessions(
                    org_client, sts_client, role_to_assume, account_ids
                )
            )
            valid_sessions = [
                session for session in sessions if session.assume_role_success is True
            ]
            invalid_sessions = [
                session.format_cove_error()
                for session in sessions
                if session.assume_role_success is False
            ]

            if invalid_sessions:
                logger.warning("Could not assume role into these accounts:")
                for invalid_session in invalid_sessions:
                    logger.warning(invalid_session)
                invalid_ids = [failure["Id"] for failure in invalid_sessions]
                logger.warning(
                    f"\n\nInvalid session Account IDs as list: {invalid_ids}"
                )

            if not valid_sessions:
                raise ValueError("No accounts are accessible: check logs for detail")

            results, exceptions = asyncio.run(
                _async_boto3_call(
                    valid_sessions, raise_exception, func, *args, **kwargs
                )
            )
            return {
                "Results": results,
                "Exceptions": exceptions,
                "FailedAssumeRole": invalid_sessions,
            }

        return wrapper

    # Handle both bare decorator and with argument
    if _func is None:
        return decorator
    else:
        return decorator(_func)

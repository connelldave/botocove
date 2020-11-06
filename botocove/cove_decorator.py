import asyncio
import functools
import logging
from concurrent import futures
from typing import List, Optional, Set

import boto3
from boto3 import Session

logger = logging.getLogger(__name__)

DEFAULT_ROLENAME = "OrganizationAccountAccessRole"


def get_account_session(sts_client, account_id, rolename) -> Session:
    role_arn = f"arn:aws:iam::{account_id}:role/{rolename}"
    logger.debug(f"Attempting to assume {role_arn}")
    creds = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=rolename)[
        "Credentials"
    ]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def get_org_accounts(
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

    active_accounts = set(
        acc["Id"] for acc in all_org_accounts if acc["Status"] == "ACTIVE"
    )

    target_accounts = active_accounts - accounts_to_ignore
    logger.info(f"Target accounts for Cove function: {target_accounts}")
    if not target_accounts:
        raise ValueError("No accounts supplied to run Cove against")
    return target_accounts


def cove(
    _func=None, *, target_ids=None, ignore_ids=None, rolename=None, org_session=None
):
    def async_decorator(func):
        @functools.wraps(func)
        def wrapper():
            if not org_session:
                # If undefined, use credentials from boto3 credential chain
                logger.info("No Boto3 session argument: using credential chain")
                sts_client = boto3.client("sts")
                org_client = boto3.client("organizations")
            else:
                # Use boto3 session supplied as arg
                logger.info(
                    f"Boto3 session {org_session} argument provided: using to create "
                )
                sts_client = org_session.client("sts")
                org_client = org_session.client("organizations")

            # Create a set of account ID's to run function against
            if not target_ids:
                accounts = get_org_accounts(org_client, sts_client, ignore_ids)
            elif ignore_ids:
                accounts = set(target_ids) - set(ignore_ids)
            else:
                accounts = set(target_ids)

            # Role to assume in each account
            if not rolename:
                # If undefined, use default AWS organization role
                role_to_assume = DEFAULT_ROLENAME
            else:
                # Use supplied role name
                role_to_assume = rolename

            logger.info(f"arguments: {role_to_assume=} {target_ids=} {ignore_ids=}")
            logger.debug(f"Accounts targeted are: {accounts}")

            async def async_boto3_call(accounts):
                logger.info(f"Running decorated func {func.__name__}")
                with futures.ThreadPoolExecutor() as executor:
                    loop = asyncio.get_running_loop()
                    tasks = []
                    failed_account_access = {}
                    for account_id in accounts:
                        try:
                            account_session = get_account_session(
                                sts_client, account_id, role_to_assume
                            )
                            tasks.append(
                                loop.run_in_executor(executor, func, account_session)
                            )
                        except Exception as e:
                            failed_account_access[account_id] = e
                            logger.debug(f"Exception caused with {account_id}: {e}")
                            continue

                    if failed_account_access:
                        logger.warning(
                            f"Could not assume {role_to_assume} in these accounts: "
                            f"{failed_account_access.items()}"
                        )

                    if tasks:
                        completed, _ = await asyncio.wait(tasks)
                        results = [t.result() for t in completed]

                    else:
                        raise Exception(
                            "No accounts are accessible: check logs for detail"
                        )

                return results

            all_account_results = asyncio.run(async_boto3_call(accounts))
            return all_account_results

        return wrapper

    # Handle both bare decorator and with argument
    if _func is None:
        return async_decorator
    else:
        return async_decorator(_func)

import asyncio
from concurrent import futures
import functools
import boto3
from boto3 import Session
import logging
from typing import Set, Optional, List

logging.basicConfig()
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
        region_name="eu-west-1",
    )


def get_org_accounts(sts_client, ignore_ids: Optional[List[str]]) -> Set[str]:
    calling_account = set(boto3.client("sts").get_caller_identity()["Account"])
    accounts_to_ignore = set(calling_account)

    if ignore_ids:
        accounts_to_ignore = set(ignore_ids) | accounts_to_ignore

    all_org_accounts = (
        boto3.client("organizations")
        .get_paginator("list_accounts")
        .paginate()
        .build_full_result()["Accounts"]
    )

    active_accounts = set(
        acc["Id"] for acc in all_org_accounts if acc["Status"] == "ACTIVE"
    )

    return active_accounts - accounts_to_ignore


def cove(_func=None, *, target_ids=None, ignore_ids=None, rolename=None, session=None):
    def async_decorator(func):
        @functools.wraps(func)
        def wrapper():
            if not session:
                # If undefined, use credentials from boto3 credential chain
                sts_client = boto3.client("sts")
            else:
                # Use boto3 session supplied as arg
                sts_client = session.client("sts")

            # Create a set of account ID's to run function against
            if not target_ids:
                accounts = get_org_accounts(sts_client, ignore_ids)
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
                            tasks.append(
                                loop.run_in_executor(
                                    executor,
                                    func,
                                    get_account_session(
                                        sts_client, account_id, role_to_assume
                                    ),
                                )
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

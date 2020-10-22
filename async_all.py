import asyncio
from concurrent import futures
import functools
import boto3
from boto3 import Session
import logging
from typing import Set

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ROLENAME = "OrganizationAccountAccessRole"
DEFAULT_ROLENAME = "OrganizationAccountReadOnlyRole"


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


def get_all_org_accounts() -> Set[str]:
    all_accounts = (
        boto3.client("organizations")
        .get_paginator("list_accounts")
        .paginate()
        .build_full_result()["Accounts"]
    )
    accounts = set(acc["Id"] for acc in all_accounts if acc["Status"] == "ACTIVE")
    # Remove the organization master account
    return accounts - set(boto3.client("sts").get_caller_identity()["Account"])


def async_all(
    _func=None,
    *,
    target_ids=[],
    ignore_ids=[],
    rolename=DEFAULT_ROLENAME,
):
    def async_decorator(func):
        @functools.wraps(func)
        def wrapper():
            if _func is None:
                # Decorator has arguments
                if target_ids:
                    accounts = target_ids
                else:
                    accounts = get_all_org_accounts()
                    if ignore_ids:
                        accounts = set(accounts) - set(ignore_ids)
            else:
                # Decorator with no arguments
                accounts = get_all_org_accounts()

            sts_client = boto3.client("sts")
            logger.info(f"Running decorated func {func.__name__}")
            logger.info(f"arguments: {rolename=} {target_ids=} {ignore_ids=}")
            logger.debug(f"Accounts targeted are: {accounts}")

            async def async_boto3_call(accounts):
                with futures.ThreadPoolExecutor(max_workers=10) as executor:
                    loop = asyncio.get_running_loop()
                    tasks = []
                    failed_account_access = []
                    for account_id in accounts:
                        try:
                            tasks.append(
                                loop.run_in_executor(
                                    executor,
                                    func,
                                    get_account_session(
                                        sts_client, account_id, rolename
                                    ),
                                )
                            )
                        except Exception as e:
                            failed_account_access.append(account_id)
                            logger.debug(f"Exception caused with {account_id}: {e}")
                            continue

                    if failed_account_access:
                        logger.warning(
                            f"Could not assume {rolename} in these accounts: "
                            f"{failed_account_access}"
                        )

                    if tasks:
                        completed, _ = await asyncio.wait(tasks)
                        results = [t.result() for t in completed]

                    else:
                        raise Exception(
                            "No accounts are accessible: check debug logs for detail"
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

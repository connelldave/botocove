import asyncio
import concurrent.futures
import boto3
from timeit import default_timer as timer

ROLENAME = "OrganizationAccountAccessRole"


async def check_org_account_access(executor, all_accounts):
    loop = asyncio.get_event_loop()
    blocking_tasks = []
    sts_client = boto3.client("sts")

    for acc in all_accounts:
        blocking_tasks.append(
            loop.run_in_executor(executor, check_assume, sts_client, acc)
        )
    completed, pending = await asyncio.wait(blocking_tasks)
    results = [t.result() for t in completed]
    return results


def check_assume(sts, acc):
    result = {"Id": acc["Id"], "Name": acc["Name"]}
    try:
        assume_role(sts, acc["Id"])
        result["Success"] = True
        return result
    except Exception:
        result["Success"] = False
        return result


def assume_role(sts_client, account_id):
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLENAME}"
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=ROLENAME
    )
    return assumed_role_object["Credentials"]


def main():
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=64)
    event_loop = asyncio.get_event_loop()

    pages = boto3.client("organizations").get_paginator("list_accounts").paginate()
    all_accounts = pages.build_full_result()["Accounts"]
    print(f"There are {len(all_accounts)} AWS accounts in the organization")

    start = timer()
    check_org_account_access_results = event_loop.run_until_complete(
        check_org_account_access(executor, all_accounts)
    )
    elapsed = timer() - start
    print(f"Operation took: {elapsed}\n")

    failed = [acc for acc in check_org_account_access_results if not acc["Success"]]
    print(f"{len(failed)} accounts cannot be assumed into from Tech Billing.")

    success = [acc for acc in check_org_account_access_results if acc["Success"]]
    print(f"{len(success)} accounts assumed into from Tech Billing.")

    print(f"{len(success) + len(failed)} checked of {len(all_accounts)} total")
    print("\n\nTo fix:\n------------------------")
    for acc in failed:
        print(acc["Name"], ": ", acc["Id"])


if __name__ == "__main__":
    main()

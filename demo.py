import sys
import boto3
from botocove import cove


def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()
    return all_users


def main():

    member_account_id, repetitions = sys.argv[1:3]

    target_ids = [member_account_id] * int(repetitions)

    all_results = cove(get_iam_users, target_ids=target_ids)()

    for r in all_results["Results"]:
        print(r)

    for e in all_results["Exceptions"]:
        print(e)
        
    for f in all_results["FailedAssumeRole"]:
        print(f)


if __name__ == "__main__":
    main()

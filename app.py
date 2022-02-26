import boto3
from botocove import cove

target_ids = None #[] #["ou-gxpu-3s6crl5b"]
ignore_ids = ["ou-gxpu-kf3og5xi"]
role_name = "DTIT_StackSetRole"
assuming_session = None

@cove(target_ids=target_ids, ignore_ids=ignore_ids, rolename=role_name, assuming_session=assuming_session, raise_exception=False, org_master=False)
def get_iam_users(session):
    iam = session.client("iam", region_name="eu-central-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()
    return all_users

def main():
    # No session passed as the decorator injects it
    all_results = get_iam_users()
    # Now returns a Dict with keys Results, Exceptions and FailedAssumeRole

    # A list of dictionaries for each account, with account details included.
    # Each account's get_iam_users return is in a "Result" key.
    print(all_results["Results"])

    # A list of dictionaries for each account that raised an exception
    print(all_results["Exceptions"])

    # A list of dictionaries for each account that could not be assumed into
    print(all_results["FailedAssumeRole"])

if __name__ == '__main__':
    main()

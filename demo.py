from botocore.exceptions import ClientError
from itertools import chain
import json
import sys
import boto3
from botocove import cove

@cove()
def describe_vpcs(session):
    iam = session.client("ec2", region_name="eu-west-1")
    all_vpcs = iam.get_paginator("describe_vpcs").paginate().build_full_result()
    return all_vpcs

@cove()
def get_iam_user_that_does_not_exist(session):
    iam = session.client("iam", region_name="eu-west-1")
    return iam.get_user(UserName="does_not_exist")

def main():
    # No session passed as the decorator injects it
    all_results = chain(describe_vpcs(), get_iam_user_that_does_not_exist())

    for r in all_results:
        json.dump(r, sys.stdout, cls=BotoJSONEncoder)
        print()


class BotoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ClientError):
            return repr(obj)
        return json.JSONEncoder.default(self, obj)


if __name__ == "__main__":
    main()

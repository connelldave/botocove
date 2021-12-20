import boto3
from botocove import cove, CoveOutput

@cove()
def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()
    return all_users

def main():
    all_results = get_iam_users() 

    if type(all_results) == CoveOutput:
        # A list of dictionaries for each account, with account details included.
        # Each account's get_iam_users return is in a "Result" key.
        print(all_results["Results"]) 
        
        # A list of dictionaries for each account that raised an exception
        print(all_results["Exceptions"])

        # A list of dictionaries for each account that could not be assumed into
        print(all_results["FailedAssumeRole"])

    else:
        invalid_sessions, results, exceptions = all_results

        for i in invalid_sessions:
            print(i)
        
        for r in results:
            print(r)
        
        for e in exceptions:
            print(e)


if __name__ == "__main__":
    main()

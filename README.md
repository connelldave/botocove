# botocove

This is a simple decorator for functions to run them against all AWS accounts in an organization. Wrap a function in `@cove` and inject a session from every AWS account in
your org!

Credential requirements are:
In the calling account:
* IAM permissions `sts:assumerole`, `sts:get-caller-identity` and `organizations:list-accounts`
* From an account that is trusted by other account roles: primarily, an AWS organization master account.
In the organization accounts:
* A trust relationship to the calling account
* Whatever IAM permisisons your wrapped function is using.

## Quickstart
Wrapping a function that is usually passed a boto3 `session` can now be called with
a `session` from every account required in your AWS organization, assuming a role in
each account.

For example:

This function takes a boto3 `session` and gets the IAM users from an AWS account

```

def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.list_users
    all_users = iam.get_paginator("list_users").paginate().build_full_result()

    return all_users

def main():
    session = boto3.session.Session(profile_name="my_dev_account")
    users = get_iam_users(session)
    print(users) # A single account's IAM users
```

This decorated function is not called with a `session` from `main()` and instead has a `session` injected by the decorator for every account your credentials can assume a role in to. It returns a list of every account that can be accessed and their IAM users.

```
@cove
def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.list_users
    all_users = iam.get_paginator("list_users").paginate().build_full_result()

    return all_users

def main():
    session = boto3.session.Session(profile_name="my_org_master")
    all_users = get_iam_users()
    print(all_users) # A list of all responses from IAM's list_users API for every account in the AWS organization
```

### botocove?

It turns out that the Amazon's Boto dolphins are soliditary or small-group animals,
unlike the large pods of dolphins in the oceans. This killed my "large group of boto"
idea, so the next best idea was where might they all shelter together... a cove!
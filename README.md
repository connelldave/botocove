# Botocove

Run code against all AWS accounts in an organization asyncronously.

A simple decorator for function to run them against all AWS accounts in an 
organization. Removes time and complexity burden, can access and
run commands against 200 organization accounts in 10 seconds. Extends `boto3`
using `async.io`.

Wrap a function in `@cove` and inject an assumed role session from every AWS 
account in an org and return results to a dictionary.

**Warning**: this tool gives you the potential to make dangerous changes
at scale. **Test carefully and make idempotent changes**! Please read available
arguments to understand safe experimentation with this package.

## Requirements

An IAM user in an AWS Organization master account that can assume roles in
organization member AWS accounts.

Credential requirements are:

In the organization master account:
* IAM permissions `sts:assumerole`, `sts:get-caller-identity` and `organizations:list-accounts`

In the organization accounts:
* A trust relationship to the calling account
* IAM permissions required for your wrapped function.

## Quickstart
A function written to interact with a `boto3 session` can now be called with
a `session` from every account required in your AWS organization, assuming
a role in each account.

For example:

This function takes a boto3 `session` and gets all IAM users from a single AWS
account

```
import boto3


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

Now with `@cove`: a session for every account in the organization is injected
by the decorator.

```
import boto3
from botocove import cove

# Only required if credentials in the boto3 chain are not suitable
org_session = boto3.session.Session(profile_name="my_org_master")


@cove(org_session=org_session)
def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.list_users
    all_users = iam.get_paginator("list_users").paginate().build_full_result()

    return all_users

def main():
    all_results = get_iam_users()
    # A list of dictionaries of all responses from above get_iam_users() for 
    # every account in the AWS organization and their account details
    print(all_results["Results"])
    # A list of dictionaries of any exceptions raised by your wrapped function
    # and the account's details
    print(all_results["Exceptions"])
    # A list of dictionaries of all accounts that could not be assumed into
    # and that account's details
    print(all_results["FailedAssumeRole"])
```

## Arguments

### Cove
`@cove`: Uses boto3 credential chain to get every AWS account within the organization.
Equivialent to:
`@cove(target_ids=None, ignore_ids=None, rolename=None, org_session=None, raise_exception=False)`

`target_ids`: Optional[List[str]]
A list of AWS accounts as strings to attempt to assume role in to. As
default, attempts to use every available account ID in an AWS organization.

`ignore_ids`: Optional[List[str]]
A list of AWS account ID's that will not attempt assumption in to. Allows IDs to be
ignored. Works with or without `target_ids`.

`rolename`: Optional[str]
An IAM role name that will be attempted to assume in all target accounts. Defaults to
the AWS default, `OrganizationAccountAccessRole`

`org_session`: Optional[Session]
A Boto3 `Session` object. If not provided, defaults to standard boto3 credential chain.

`raise_exception`: bool
Defaults to False. Default behaviour is that exceptions are not raised from
decorated function. This is due to `cove` running asynchronously and preferring
to resolve all tasks and report their results instead of exiting early.

`raise_exception=True` will allow a full stack trace to escape on the first
exception seen; but will not gracefully or consistently interrupt running tasks.
 It is vital to run interruptable, idempotent code with this argument as `True`.

### CoveSession

Cove supplies an enriched Boto3 session to each function called. Account details
are available with the `session_information` attribute.

Otherwise, it functions exactly as calling `boto3` would.

```
@cove()
def get_all_iam_users(session: CoveSession):
    print(session.session_information) # Outputs a dict of known information
    iam = session.client("iam", region_name="eu-west-1")
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.list_users
    all_users = iam.get_paginator("list_users").paginate().build_full_result()

    return all_users
```

## Return values

Wrapped functions return a dictionary. Each value contains List[Dict[str, Any]]:
```
{
    "Results": results: 
    "Exceptions": exceptions,
    "FailedAssumeRole": invalid_sessions,
}
```
An example of cove_output["Results"]:
```
[
    {
    'Id': '123456789010',
    'Email': 'email@address.com',
    'Name': 'account-name',
    'Status': 'ACTIVE',
    'AssumeRoleSuccess': True,
    'Result': all_users # Result of above func
    } # A dictionary per account
]
```


### botocove?

It turns out that the Amazon's Boto dolphins are soliditary or small-group animals,
unlike the large pods of dolphins in the oceans. This killed my "large group of boto"
idea, so the next best idea was where might they all shelter together... a cove!
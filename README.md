# Botocove

Run a function against a selection of AWS accounts, or all AWS accounts in an
organization, concurrently. By default, opinionated to work with the standard
AWS Organization master/member configuration from an organization master
account.

- Fast
- Easy
- Dolphin Themed 🐬

A simple decorator for functions to remove time and complexity burden. Uses
`async.io` and `ThreadPoolExecutor` to run boto3 sessions against one to all
of your AWS accounts at (nearly!) the same speed as running against one.

Wrap a function in `@cove` and inject an assumed role session into every account
required, gathering all results into a dictionary.

**Warning**: this tool gives you the potential to make dangerous changes
at scale. **Test carefully and make idempotent changes**! Please read available
arguments to understand safe experimentation with this package.

## Requirements

An IAM user with `sts:assumerole` privilege, and accounts that have a trust
relationship to the IAM user's account.

By default, the IAM user is expected to be in an AWS Organization Master account

Default (customisable if unsuitable) expectations are:

In the organization master account:
* IAM permissions `sts:assumerole`, `sts:get-caller-identity` and
`organizations:list-accounts`

In the organization accounts:
* An `AccountOrganizationAccessRole` role

See the Arguments section for how to change these defaults to work with any
accounts.

## Quickstart
A function written to interact with a `boto3 session` can now be called with
a `session` from every account required in your AWS organization, assuming
a role in each account.

For example:

A standard approach: this function takes a boto3 `session` and gets all IAM
users from a single AWS account

```
import boto3


def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()
    return all_users

def main():
    session = boto3.session.Session(profile_name="my_dev_account")
    users = get_iam_users(session)
    print(users) # A single account's IAM users
```

Now with `@cove`: a session for every account in the organization is injected
by the decorator. A safe example to run as a test!

```
import boto3
from botocove import cove

@cove()
def get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
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
```

## Arguments

### Cove
`@cove()`: Uses boto3 credential chain to get every AWS account within the
organization, assume the `OrganizationAccountAccessRole` in it and run the
wrapped function with that role.

Equivalent to:
`@cove(target_ids=None, ignore_ids=None, rolename=None, assuming_session=None, 
    raise_exception=False, org_master=True)`

`target_ids`: Optional[List[str]]
A list of AWS accounts as strings to attempt to assume role in to. When unset,
default attempts to use every available account ID in an AWS organization.

`ignore_ids`: Optional[List[str]]
A list of AWS account ID's that will not attempt assumption in to. Allows IDs to
be ignored.

`rolename`: Optional[str]
An IAM role name that will be attempted to assume in all target accounts. 
Defaults to the AWS Organization default, `OrganizationAccountAccessRole`.

`role_session_name`: Optional[str]
An IAM role session name that will be passed to the `sts.assume_role()` call. 
Defaults to the AWS Organization default, `OrganizationAccountAccessRole`.

`assuming_session`: Optional[Session]
A Boto3 `Session` object that will be used to call `sts:assumerole`. If not
provided, defaults to standard boto3 credential chain.

`raise_exception`: bool
Defaults to False. Default behaviour is that exceptions are not raised from
decorated function. This is due to `cove` running asynchronously and preferring
to resolve all tasks and report their results instead of exiting early.

`raise_exception=True` will allow a full stack trace to escape on the first
exception seen; but will not gracefully or consistently interrupt running tasks.
 It is vital to run interruptible, idempotent code with this argument as `True`.

`org_master`: bool
Defaults to True. When True, will leverage the Boto3 Organizations API to list
all accounts in the organization, and enrich each `CoveSession` with information
available (`Id`, `Arn`, `Name`). 

`org_master=False` means `target_ids` must be provided (as no list of accounts
can be created for you), as well as likely `rolename`. Only `Id` will be
available to `CoveSession`.

### CoveSession

Cove supplies an enriched Boto3 session to each function called. Account details
are available with the `session_information` attribute.

Otherwise, it functions exactly as calling `boto3` would.

```
@cove()
def do_nothing(session: CoveSession):
    print(session.session_information) # Outputs a dict of known information
    # This function runs no boto3-specific API, but does test that a role
    # can be assumed
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
[ # A list of dictionaries per account called
    {
    'Id': '123456789010',
    'Email': 'email@address.com',
    'Name': 'account-name',
    'Status': 'ACTIVE',
    'AssumeRoleSuccess': True,
    'Result': wrapped_function_return_value # Result of wrapped func
    } 
] 
```

### botocove?

It turns out that the Amazon's Boto dolphins are solitary or small-group animals,
unlike the large pods of dolphins in the oceans. This killed my "large group of 
boto" idea, so the next best idea was where might they all shelter together... a
cove!

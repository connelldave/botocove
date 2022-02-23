# Botocove

Run a function against a selection of AWS accounts, or all AWS accounts in an
organization, concurrently with thread safety. Run in one or multiple regions.

By default, opinionated to work with the standard
AWS Organization master/member configuration from an organization master
account.

- Fast
- Easy
- Dolphin Themed 🐬

A simple decorator for functions to remove time and complexity burden. Uses
`ThreadPoolExecutor` to run boto3 sessions against AWS accounts concurrently.

Decorating a function in `@cove` provides a boto3 session to the function and runs it
in every account required, gathering all results into a dictionary.

**Warning**: this tool gives you the potential to make dangerous changes
at scale. **Test carefully and make idempotent changes**! Please read available
arguments to understand safe experimentation with this package.

## Pre-requisites and Info

An IAM user with `sts:assumerole` privilege, and accounts that have a trust
relationship to the IAM user's account.

By default, the IAM user is expected to be in an AWS Organization Master account. You can alter nearly all behaviour of Cove with appropriate [arguments](#arguments)

Cove will not execute a function call in the account it's called from.

Default requirements are:

In the organization master account:
* IAM permissions `sts:assumerole`, `sts:get-caller-identity` and
`organizations:list-accounts`

In the organization accounts:
* An `AccountOrganizationAccessRole` role

See the [arguments](#arguments) section for how to change these defaults to work with any
account configuration, including running without an AWS Organization.

## Quickstart
A function written to interact with one
[boto3 session](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html)
can now be called with a `session` from every account and region required by assuming a
 role in for each account - except the host account you're running from.

For example:

A standard approach: this function takes a boto3 `session` and gets all IAM
users from a single AWS account. You would then manually run it in each account.

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

Here's an example of a more customised Cove decorator:
```
@cove(
    target_ids=["123456789101", "234567891011"],
    rolename="AWSControlTowerExecution",
    raise_exception=True,
    regions=["eu-west-1", "eu-west-2", "us-east-1"],
)
def do_things(session):
    # Cove will return six results of True, 2 accounts * 3 regions
    return True
```
## Arguments

### Cove
`@cove()`:

Uses the standard boto3 credential chain to start with, assuming roles in every account
required. Defaults to assuming the `OrganizationAccountAccessRole` in every account
in an AWS organization.

Equivalent to:
`@cove(target_ids=None, ignore_ids=None, rolename=None, role_session_name=rolename,
    policy=None, policy_arns=None, assuming_session=None, raise_exception=False,
    org_master=True, thread_workers=20, regions=None)`

`target_ids`: List[str]

A list of AWS accounts as strings to attempt to assume role in to. When unset,
default attempts to use every available account ID in an AWS organization.

`ignore_ids`: List[str]

A list of AWS account ID's that will not attempt assumption in to. Allows IDs to
be ignored.

`rolename`: str

An IAM role name that will be attempted to assume in all target accounts.
Defaults to the AWS Organization default, `OrganizationAccountAccessRole`.

`role_session_name`: str

An IAM role session name that will be passed to each Cove session's `sts.assume_role()` call.
Defaults to the name of the role being used if unset.

`policy`: str

A policy document that will be used as a session policy in each Cove session's `sts.assume_role()`
call. Unless the value is None, it is passed through via the Policy parameter.

`policy_arns`: List[str]

A list of managed policy ARNs that will be used as a session policy in each Cove session's
 `sts.assume_role()` call. Unless the value is None, it is passed through via the PolicyArns parameter.

`assuming_session`: Session

A Boto3 `boto3.session.Session()` object that will be used to call `sts:assumerole`. If not
provided, cove will instantiate one which will use the standard boto3 credential chain.

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
available (`Id`, `Arn`, `Name`, `Status`, `Email`). Disabling this and providing your
own full list of accounts may be a desirable optimisation if speed is an issue.

`org_master=False` means only `Id` will be
available to `CoveSession`.

`thread_workers`: int

Defaults to 20. Cove utilises a ThreadPoolWorker under the hood, which can be tuned
with this argument. Number of thread workers directly corrolates to memory usage: see
[here](#is-botocove-thread-safe)

`regions`: List[str]

If not provided, Cove will respect your profile's default region via the boto credential chain.
If provided, Cove will run the decorated function in every region named.

You can get all regions with:
`regions = [r['RegionName'] for r in boto3.client('ec2').describe_regions()['Regions']]`✨

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

### Is botocove thread safe?

botocove is thread safe, but number of threaded executions will be bound by memory,
network IO and AWS api rate limiting. Defaulting to 20 thread workers is a reasonable
starting point, but can be further optimised for runtime with experimentation.

botocove has no constraint or understanding of the function it's wrapping: it is
recommended to avoid shared state for botocove wrapped functions, and to write simple
functions that are written to be idempotent and independent.

[Boto3 Session objects are not natively thread safe and should not be shared across threads](https://boto3.amazonaws.com/v1/documentation/api/1.14.31/guide/session.html#multithreading-or-multiprocessing-with-sessions).
However, botocove is instantiating a new Session object per thread/account and running
decorated functions inside their own closure. A shared client is used from the host account
that botocove is run from (eg, an organization master account) -
[clients are threadsafe](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/clients.html#multithreading-or-multiprocessing-with-clients) and allow this.

boto3 sessions have a significant memory footprint:
Version 1.5.0 of botocove was re-written to ensure that boto3 sessions are released
after completion which resolved memory starvation issues. This was discussed here:
https://github.com/connelldave/botocove/issues/20 and a relevant boto3 issue is here:
https://github.com/boto/boto3/issues/1670

### botocove?

It turns out that the Amazon's Boto dolphins are solitary or small-group animals,
unlike the large pods of dolphins in the oceans. This killed my "large group of
boto" idea, so the next best idea was where might they all shelter together... a
cove!

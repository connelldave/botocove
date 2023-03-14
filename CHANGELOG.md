<!-- markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.3] - 2023-18-2

### Added

Adds support for providing a non-`aws` partition value

## [1.7.2] - 2023-18-2

Adds py.typed file to behave properly for mypy.

## [1.7.1] - 2022-20-12

Replaces 1.7.0 which was yanked from pypi after an accidental Python version bump
was released - reverted in 1.7.1

## [1.7.0] - 2022-16-12

### Changed

- This release fixes a regression around how `target_ids` are handled. If
`target_ids` were provided as `[]`, the intent is no accounts would be targeted.
However, this was being treated as `None` and if in an Organization context,
would return all Organization accounts instead.

We are releasing this as a minor version bump in case anyone has ended up with
this misbehaviour as a dependency, but hopefully this will not be a breaking
change for anyone.

### Added

- `target_ids` is now typechecked to assert is correctly formed as `list[str]`,
a list with more than one string.

## [1.6.4] - 2022-28-11

### Added

- Botocove now supports an external id argument that will be passed to each Cove
session's `sts.assume_role()` call

## [1.6.3] - 2022-9-10

### Added

- Botocove now has a simple typecheck for the account_ids kwarg to assert a list
  has been provided rather than a string.

### Fixed

- Removed references to `org_master` kwarg and added deprecration warning

## [1.6.2] - 2022-14-09

### Added

- Botocove now has a simple typecheck for the regions kwarg to assert a list
  has been provided rather than a string.

### Fixed

- Botocove no longer calls DescribeAccount per account when running in an AWS
  organization.
- `org_master` is now a deprecated kwarg: Botocove will optimistically check for
  permission
  to an AWS Organization to list accounts, and fall back to not adding metadata to
  CoveSession.

## [1.6.1] - 2022-04-03

### Fixed

- Botocove's progress bar in TTY mode is now incremental as each account function
  returns rather than blocking on slowest thread in a batch.

## [1.6.0] - 2022-04-03

### Added

- Botocove now supports AWS Organizational Unit IDs as a target and ignore ID. Child
  accounts and OUs will be recursively discovered and targeted for the passed OU
  ID.

## [1.5.2] - 2022-23-02

### Added

- Botocove now supports a regions argument, allowing sessions to be run across
  one or many regions per account

## [1.5.1] - 2022-13-02

### Fixed

- Reverted internal handling of output data to a dictionary rather than dataclass:
  issues with recursive copy required to output dataclass as dict.

## [1.5.0] - 2022-06-02

### Added

- thread_workers argument

### Fixed

- Memory leak when running in large organizations: botocove now allows
  completed Session objects to be garbage collected

## [1.4.1] - 2022-15-01

### Added

- Support for Policy and PolicyArn restriction on assumed roles

## [1.4.0] - 2021-15-11

### Added

- Progress bar when running in TTY environment
- Strong typing: refactor underlying code without changing external behaviour
- Moved to simpler threading behaviour

### Fixed

- Fixed missing RoleSessionName when not using Cove's organisation master
  session information enrichment

### Removed

- Use of async.io loop

## [1.3.0] - 2021-07-1

### Added

- Added option to set a custom `RoleSessionName` parameter in
  `sts.assume_role()` calls for the `cove` decorator.

## [1.3.1] - 2021-27-9

### Fixed

- Fixed bug where a large amount of accounts would cause the AWS DescribeAccount
  api to throttle and throw an exception

## [1.3.0] - 2021-07-1

### Added

- Added option to set a custom `RoleSessionName` parameter in
  `sts.assume_role()` calls for the `cove` decorator.

## [1.2.0] - 2021-26-3

### Added

- Add a TypedDict for CoveOutput

### Fixed

- Fixed bug where passing empty list to target IDs would fetch all org accounts.
- Improved fixture breaking Boto3 credentials in tests

## [1.1.0] - 2020-14-8

### Added

- Support for assuming roles from accounts that are not AWS Organization masters
  via the org_master=False argument.
- Changelog!
- Add full typing and mypy to linting CI
- Defensive typing around `ignore_ids`

### Changed

- Moved to LGPLv3 licencing

### Fixed

- Fixed bug where Organization Master would not filter it's own account ID out.

## [1.0.0] - 2020-11-8

### Added

- First release

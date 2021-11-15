# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2021-15-11
### Added
- Progress bar when running in TTY environment
- Strong typing: refactor underlying code without changing external behaviour
- Moved to simpler threading behaviour
### Fixed
- Fixed missing RoleSessionName when not using Cove's organisation master session information enrichment
### Removed
- Use of async.io loop

## [1.3.0] - 2021-07-1
### Added
- Added option to set a custom `RoleSessionName` parameter in `sts.assume_role()` calls for the `cove` decorator.
## [1.3.1] - 2021-27-9
### Fixed
- Fixed bug where a large amount of accounts would cause the AWS DescribeAccount api to throttle and throw an exception
## [1.3.0] - 2021-07-1
### Added
- Added option to set a custom `RoleSessionName` parameter in `sts.assume_role()` calls for the `cove` decorator.
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
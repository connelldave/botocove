# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
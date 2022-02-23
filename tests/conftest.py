import logging
from typing import Iterator

import boto3
import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from moto import mock_organizations, mock_sts

from tests.moto_mock_org.moto_models import LargeOrg, SmallOrg


@pytest.fixture(autouse=True)
def _set_log_level(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: MonkeyPatch) -> None:
    env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    # Setting bad credentials invalidates file-based credentials too
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials
    for env_var in env_vars:
        monkeypatch.setenv(env_var, "broken_not_real_profile")


# We tear down each fixture in the default function scope as Moto isn't thread-safe
# Maintaining Moto mocks between tests means shared state mutation
# We could just use one mock org instead - option for future.
@pytest.fixture()
def mock_small_org() -> Iterator[SmallOrg]:
    """Uses moto mocking library to allow creation of fake AWS environment."""
    with mock_sts():
        with mock_organizations():
            session = boto3.session.Session()
            yield SmallOrg(session=session)


@pytest.fixture()
def mock_large_org() -> Iterator[LargeOrg]:
    """Uses moto mocking library to allow creation of fake AWS environment."""
    with mock_sts():
        with mock_organizations():
            session = boto3.session.Session()
            yield LargeOrg(session=session)

import logging
from typing import Iterator

import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from boto3 import Session
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


@pytest.fixture()
def mock_session() -> Iterator[Session]:
    """Returns a session with mock AWS services."""
    with mock_sts(), mock_organizations():
        yield Session()


# We tear down each fixture in the default function scope as Moto isn't thread-safe
# Maintaining Moto mocks between tests means shared state mutation
# We could just use one mock org instead - option for future.
@pytest.fixture()
def mock_small_org(mock_session: Session) -> SmallOrg:
    """Uses moto mocking library to allow creation of fake AWS environment."""
    return SmallOrg(session=mock_session)


@pytest.fixture()
def mock_large_org(mock_session: Session) -> LargeOrg:
    """Uses moto mocking library to allow creation of fake AWS environment."""
    return LargeOrg(session=mock_session)

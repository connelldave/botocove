import logging
import os

import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture(autouse=True)
def set_log_level(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: MonkeyPatch) -> None:
    env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE"]
    for env_var in env_vars:
        if env_var in os.environ:
            monkeypatch.delenv(env_var)

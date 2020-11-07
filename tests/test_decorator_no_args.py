from unittest.mock import MagicMock

import pytest

from botocove.cove_decorator import cove


@pytest.fixture
def patch_boto3_client(mocker) -> MagicMock:
    mock_boto3 = mocker.patch("botocove.cove_decorator.boto3")
    list_accounts_result = {
        "Accounts": [
            {"Id": "12345689012", "Status": "ACTIVE"},
            {"Id": "12345689013", "Status": "ACTIVE"},
        ]
    }
    mock_boto3.client.return_value.get_paginator.return_value.paginate. \
        return_value.build_full_result.return_value = (
            list_accounts_result
        )
    return mock_boto3


def test_decorated_simple_func(patch_boto3_client) -> None:
    @cove
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output) == 2

from botocove.cove import cove
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def patch_boto3_session(mocker) -> MagicMock:
    # mock_session = MagicMock()
    # list_accounts_result = {
    #     "Accounts": [
    #         {"Id": "12345689012", "Status": "ACTIVE"},
    #         {"Id": "12345689013", "Status": "ACTIVE"},
    #     ]
    # }
    # mock_session.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (
    #     list_accounts_result
    # )
    # # Mock out the credential requiring API call
    return mocker.patch("..botocove.cove.boto3")


def test_decorated_simple_func(patch_boto3_session) -> None:
    @cove
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output) == 2
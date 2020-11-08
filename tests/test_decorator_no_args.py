from typing import Tuple
from unittest.mock import MagicMock

import pytest

from botocove.cove_decorator import cove


@pytest.fixture()
def patch_boto3_client(mocker) -> MagicMock:
    mock_boto3 = mocker.patch("botocove.cove_decorator.boto3")
    list_accounts_result = {"Accounts": [{"Id": "12345689012", "Status": "ACTIVE"}]}
    mock_boto3.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    describe_account_results = [{"Account": {"Id": "123"}}]
    mock_boto3.client.return_value.describe_account.side_effect = (
        describe_account_results
    )
    return mock_boto3


def test_decorated_simple_func(patch_boto3_client) -> None:
    @cove
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    expected = [{"Id": "123", "AssumeRoleSuccess": True, "Result": "hello"}]
    assert cove_output["Results"] == expected


def test_decorated_func_passed_arg(patch_boto3_client) -> None:
    @cove
    def simple_func(session, output) -> str:
        return output

    cove_output = simple_func("blue")
    expected = [{"Id": "123", "AssumeRoleSuccess": True, "Result": "blue"}]
    assert cove_output["Results"] == expected


def test_decorated_func_passed_arg_and_kwarg(patch_boto3_client) -> None:
    @cove
    def simple_func(session, time, colour, shape) -> Tuple[str, str, str]:
        return colour, shape, time

    cove_output = simple_func("11:11", shape="circle", colour="blue")["Results"]
    # Call with an arg and two kwargs
    expected = [
        {"Id": "123", "AssumeRoleSuccess": True, "Result": ("blue", "circle", "11:11")}
    ]
    # Two simple_func calls == two mock AWS accounts
    assert cove_output == expected

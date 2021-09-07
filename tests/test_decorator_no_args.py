from datetime import datetime
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from botocove import CoveSession, cove


@pytest.fixture()
def patch_boto3_client(mocker: MockerFixture) -> MagicMock:
    mock_boto3 = mocker.patch("botocove.cove_sessions.boto3")
    list_accounts_result = {"Accounts": [{"Id": "12345689012", "Status": "ACTIVE"}]}
    mock_boto3.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    describe_account_results = [
        {
            "Account": {
                "Id": "1234",
                "Arn": "hello-arn",
                "Email": "email@address.com",
                "Name": "an-account-name",
                "Status": "ACTIVE",
                "JoinedMethod": "CREATED",
                "JoinedTimestamp": datetime(2015, 1, 1),
            }
        }
    ]
    mock_boto3.client.return_value.describe_account.side_effect = (
        describe_account_results
    )
    return mock_boto3


def test_decorated_simple_func(patch_boto3_client: MagicMock) -> None:
    @cove
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    expected = [
        {
            "Id": "12345689012",
            "Arn": "hello-arn",
            "Email": "email@address.com",
            "Name": "an-account-name",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": "hello",
        }
    ]
    assert cove_output["Results"] == expected


def test_decorated_func_passed_arg(patch_boto3_client: MagicMock) -> None:
    @cove
    def simple_func(session: CoveSession, output: str) -> str:
        return output

    cove_output = simple_func("blue")
    expected = [
        {
            "Id": "12345689012",
            "Arn": "hello-arn",
            "Email": "email@address.com",
            "Name": "an-account-name",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": "blue",
        }
    ]
    assert cove_output["Results"] == expected


def test_decorated_func_passed_arg_and_kwarg(patch_boto3_client: MagicMock) -> None:
    @cove
    def simple_func(
        session: CoveSession, time: str, colour: str, shape: str
    ) -> Tuple[str, str, str]:
        return colour, shape, time

    cove_output = simple_func("11:11", shape="circle", colour="blue")["Results"]
    # Call with an arg and two kwargs
    expected = [
        {
            "Id": "12345689012",
            "Arn": "hello-arn",
            "Email": "email@address.com",
            "Name": "an-account-name",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": ("blue", "circle", "11:11"),
        }
    ]
    # Two simple_func calls == two mock AWS accounts
    assert cove_output == expected

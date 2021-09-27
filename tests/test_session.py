from datetime import datetime
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from botocove.cove_decorator import cove


@pytest.fixture()
def patch_boto3_client(mocker) -> MagicMock:
    mock_boto3 = mocker.patch("botocove.cove_decorator.boto3")
    list_accounts_result = {"Accounts": [{"Id": "12345689012", "Status": "ACTIVE"}]}
    mock_boto3.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    describe_account_result = {
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
    mock_boto3.client.return_value.describe_account.return_value = (
        describe_account_result
    )
    return mock_boto3


def test_session_result_formatter(patch_boto3_client) -> None:
    @cove
    def simple_func(session, a_string):
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "AssumeRoleSuccess": True,
            "Email": "email@address.com",
            "Id": "1234",
            "Name": "an-account-name",
            "Result": "test-string",
            "Status": "ACTIVE",
        }
    ]
    assert cove_output["Results"] == expected


def test_session_result_error_handler(patch_boto3_client) -> None:
    # Raise an exception instead of an expected response from boto3
    patch_boto3_client.client.return_value.describe_account.side_effect = MagicMock(
        side_effect=ClientError(
            {"Error": {"Message": "broken!", "Code": "OhNo"}}, "describe_account"
        )
    )

    @cove
    def simple_func(session, a_string):
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": "12345689012",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
        }
    ]
    assert cove_output["Results"] == expected

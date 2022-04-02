from datetime import datetime
from typing import List, cast
from unittest.mock import MagicMock

import pytest
from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_organizations.type_defs import AccountTypeDef
from pytest_mock import MockerFixture

from botocove import CoveSession, cove


@pytest.fixture()
def org_accounts(mock_session: Session) -> List[AccountTypeDef]:
    """Returns a list of the accounts in the mock org. Index 0 is the management
    account."""
    org = mock_session.client("organizations")
    org.create_organization(FeatureSet="ALL")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    return org.list_accounts()["Accounts"]


@pytest.fixture()
def patch_boto3_client(mocker: MockerFixture) -> MagicMock:
    mock_boto3 = mocker.patch("botocove.cove_host_account.boto3")
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


@pytest.mark.usefixtures("mock_session")
def test_session_result_formatter(org_accounts: List[AccountTypeDef]) -> None:
    @cove
    def simple_func(session: CoveSession, a_string: str) -> str:
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
        }
    ]
    assert cove_output["Results"] == expected


@pytest.mark.usefixtures("mock_session")
def test_session_result_formatter_with_policy(
    org_accounts: List[AccountTypeDef],
) -> None:
    session_policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'  # noqa: E501

    @cove(policy=session_policy)
    def simple_func(session: CoveSession, a_string: str) -> str:
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Policy": session_policy,
        }
    ]
    assert cove_output["Results"] == expected


@pytest.mark.usefixtures("mock_session")
def test_session_result_formatter_with_policy_arn(
    org_accounts: List[AccountTypeDef],
) -> None:
    session_policy_arns = cast(
        List[str], [{"arn": "arn:aws:iam::aws:policy/IAMReadOnlyAccess"}]
    )

    @cove(policy_arns=session_policy_arns)
    def simple_func(session: CoveSession, a_string: str) -> str:
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "PolicyArns": session_policy_arns,
        }
    ]
    assert cove_output["Results"] == expected


def test_session_result_error_handler(patch_boto3_client: MagicMock) -> None:
    # Raise an exception instead of an expected response from boto3
    patch_boto3_client.client.return_value.describe_account.side_effect = MagicMock(
        side_effect=ClientError(
            {"Error": {"Message": "broken!", "Code": "OhNo"}}, "describe_account"
        )
    )

    @cove()
    def simple_func(session: CoveSession, a_string: str) -> str:
        return a_string

    # Only one account for simplicity
    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": "12345689012",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
        }
    ]
    assert cove_output["Results"] == expected

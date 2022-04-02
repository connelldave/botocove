from typing import List

import botocore
import botocore.client
import pytest
from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_organizations.type_defs import AccountTypeDef
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef
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
    session_policy_arns: List[PolicyDescriptorTypeTypeDef] = [
        {"arn": "arn:aws:iam::aws:policy/IAMReadOnlyAccess"}
    ]

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


@pytest.mark.usefixtures("mock_session")
def test_session_result_error_handler(
    org_accounts: List[AccountTypeDef], mocker: MockerFixture
) -> None:
    # Raise an exception instead of an expected response from boto3.
    # See "How to test ClientError with moto?".
    # https://github.com/spulec/moto/issues/4453
    _make_api_call = (
        botocore.client.BaseClient._make_api_call  # type: ignore[attr-defined]
    )

    def fail_on_describe_account(  # type: ignore[no-untyped-def]
        self, operation_name, api_params
    ):
        if operation_name != "DescribeAccount":
            return _make_api_call(self, operation_name, api_params)
        raise ClientError(
            {"Error": {"Message": "broken!", "Code": "OhNo"}}, operation_name
        )

    mocker.patch(
        "botocore.client.BaseClient._make_api_call", new=fail_on_describe_account
    )

    @cove()
    def simple_func(session: CoveSession, a_string: str) -> str:
        return a_string

    cove_output = simple_func("test-string")
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
        }
    ]
    assert cove_output["Results"] == expected

from typing import List

import pytest
from boto3 import Session
from mypy_boto3_organizations.type_defs import AccountTypeDef
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef

from botocove import CoveSession, cove


@pytest.fixture()
def org_accounts(mock_session: Session) -> List[AccountTypeDef]:
    """Returns a list of the accounts in the mock org. Index 0 is the management
    account."""
    org = mock_session.client("organizations")
    org.create_organization(FeatureSet="ALL")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    return org.list_accounts()["Accounts"]


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
            "Partition": "aws",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Region": "eu-west-1",
        }
    ]
    assert cove_output["Results"] == expected


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
            "Partition": "aws",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Policy": session_policy,
            "Region": "eu-west-1",
        }
    ]
    assert cove_output["Results"] == expected


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
            "Partition": "aws",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": "test-string",
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "PolicyArns": session_policy_arns,
            "Region": "eu-west-1",
        }
    ]
    assert cove_output["Results"] == expected

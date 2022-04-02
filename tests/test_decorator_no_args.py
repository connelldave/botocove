from typing import List, Tuple

import pytest
from boto3 import Session
from mypy_boto3_organizations.type_defs import AccountTypeDef

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
def test_decorated_simple_func(org_accounts: List[AccountTypeDef]) -> None:
    @cove
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": "hello",
        }
    ]
    assert cove_output["Results"] == expected


@pytest.mark.usefixtures("mock_session")
def test_decorated_func_passed_arg(org_accounts: List[AccountTypeDef]) -> None:
    @cove
    def simple_func(session: CoveSession, output: str) -> str:
        return output

    cove_output = simple_func("blue")
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": "blue",
        }
    ]
    assert cove_output["Results"] == expected


@pytest.mark.usefixtures("mock_session")
def test_decorated_func_passed_arg_and_kwarg(
    org_accounts: List[AccountTypeDef],
) -> None:
    @cove
    def simple_func(
        session: CoveSession, time: str, colour: str, shape: str
    ) -> Tuple[str, str, str]:
        return colour, shape, time

    cove_output = simple_func("11:11", shape="circle", colour="blue")["Results"]
    # Call with an arg and two kwargs
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
            "Result": ("blue", "circle", "11:11"),
        }
    ]
    assert cove_output == expected

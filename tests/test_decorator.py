from typing import Iterable, List, Optional

import pytest
from boto3 import Session
from moto import mock_organizations, mock_sts
from mypy_boto3_organizations.type_defs import AccountTypeDef

from botocove import CoveSession, cove


@pytest.fixture()
def mock_session() -> Iterable[Session]:
    """Returns a session with mock AWS services."""
    with mock_sts(), mock_organizations():
        yield Session()


@pytest.fixture()
def org_accounts(mock_session: Session) -> List[AccountTypeDef]:
    """Returns a list of the accounts in the mock org. Index 0 is the management
    account."""
    org = mock_session.client("organizations")
    org.create_organization(FeatureSet="ALL")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    return org.list_accounts()["Accounts"]


@pytest.mark.usefixtures("org_accounts")
def test_decorated_simple_func(mock_session: Session) -> None:
    @cove(assuming_session=mock_session)
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output["Results"]) == 2


def test_target_and_ignore_ids(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[org_accounts[1]["Id"], org_accounts[2]["Id"]],
        ignore_ids=[org_accounts[2]["Id"]],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, two in targets, one of which is ignored.
    # simple_func calls == one target AWS accounts
    assert len(cove_output["Results"]) == 1


def test_empty_ignore_ids(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[org_accounts[1]["Id"], org_accounts[2]["Id"]],
        ignore_ids=[],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, four in targets
    # simple_func calls == two targeted AWS accounts
    print(cove_output)
    assert len(cove_output["Results"]) == 2


def test_decorated_simple_func_passed_args(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(assuming_session=mock_session, ignore_ids=[org_accounts[2]["Id"]])
    def simple_func(session: CoveSession, arg1: int, arg2: int, arg3: int) -> int:
        return arg1 + arg2 + arg3

    cove_output = simple_func(1, 2, 3)
    expected = [
        {
            "Id": org_accounts[1]["Id"],
            "Arn": org_accounts[1]["Arn"],
            "Email": org_accounts[1]["Email"],
            "Name": org_accounts[1]["Name"],
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": 6,
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
        }
    ]

    assert cove_output["Results"] == expected


@pytest.mark.usefixtures("org_accounts")
def test_decorated_simple_func_passed_session_name(mock_session: Session) -> None:
    session_name = "testSessionName"

    @cove(
        assuming_session=mock_session,
        role_session_name=session_name,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[str]:
        return session.session_information["RoleSessionName"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_name for x in cove_output["Results"])


@pytest.mark.usefixtures("org_accounts")
def test_decorated_simple_func_passed_policy(mock_session: Session) -> None:
    session_policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'  # noqa: E501

    @cove(
        assuming_session=mock_session,
        policy=session_policy,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[str]:
        return session.session_information["Policy"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_policy for x in cove_output["Results"])


@pytest.mark.usefixtures("org_accounts")
def test_decorated_simple_func_passed_policy_arn(mock_session: Session) -> None:
    session_policy_arns = ["arn:aws:iam::aws:policy/IAMReadOnlyAccess"]

    @cove(
        assuming_session=mock_session,
        policy_arns=session_policy_arns,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[List[str]]:
        return session.session_information["PolicyArns"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_policy_arns for x in cove_output["Results"])

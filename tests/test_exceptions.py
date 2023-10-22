from typing import List

import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3 import Session
from mypy_boto3_organizations.type_defs import AccountTypeDef

from botocove import cove
from botocove.cove_session import CoveSession


@pytest.fixture(autouse=True)
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


@pytest.fixture()
def org_accounts(mock_session: Session) -> List[AccountTypeDef]:
    """Returns a list of the accounts in the mock org. Index 0 is the management
    account."""
    org = mock_session.client("organizations")
    org.create_organization(FeatureSet="ALL")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    org.create_account(Email="email@address.com", AccountName="an-account-name")
    return org.list_accounts()["Accounts"]


def test_no_account_id_exception(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[org_accounts[1]["Id"]],
        ignore_ids=[org_accounts[1]["Id"]],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match="There are no eligible account ids to run decorated func against",
    ):
        simple_func()


def test_handled_exception_in_wrapped_func(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(assuming_session=mock_session, target_ids=[org_accounts[1]["Id"]])
    def simple_func(session: CoveSession) -> None:
        raise Exception("oh no")

    results = simple_func()
    expected = {
        "Id": org_accounts[1]["Id"],
        "RoleName": "OrganizationAccountAccessRole",
        "AssumeRoleSuccess": True,
        "Arn": org_accounts[1]["Arn"],
        "Email": org_accounts[1]["Email"],
        "Name": org_accounts[1]["Name"],
        "Partition": "aws",
        "Status": "ACTIVE",
        "RoleSessionName": "OrganizationAccountAccessRole",
        "ExceptionDetails": repr(Exception("oh no")),
    }

    # Compare repr of exceptions
    results["Exceptions"][0]["ExceptionDetails"] = repr(
        results["Exceptions"][0]["ExceptionDetails"]
    )

    assert results["Exceptions"][0] == expected


def test_raised_exception_in_wrapped_func(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[org_accounts[1]["Id"]],
        raise_exception=True,
    )
    def simple_func(session: CoveSession) -> None:
        raise Exception("oh no")

    with pytest.raises(Exception, match="oh no"):
        simple_func()


def test_malformed_ignore_ids(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[org_accounts[1]["Id"]],
        ignore_ids=["cat"],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match=("provided id is neither an aws account nor an ou: cat"),
    ):
        simple_func()


def test_malformed_ignore_ids_type(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=None,
        ignore_ids=[456456456456],  # type: ignore
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        TypeError,
        match=(
            "456456456456 is an incorrect type: all account and ou id's must be strings not <class 'int'>"  # noqa E501
        ),
    ):
        simple_func()


def test_malformed_target_id(
    mock_session: Session, org_accounts: List[AccountTypeDef]
) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=["xu-gzxu-393a2l5b"],
        ignore_ids=[org_accounts[1]["Id"]],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match=("provided id is neither an aws account nor an ou: xu-gzxu-393a2l5b"),
    ):
        simple_func()


def test_malformed_target_id_type(mock_session: Session) -> None:
    @cove(
        assuming_session=mock_session,
        target_ids=[456456456456],  # type: ignore
        ignore_ids=[],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        TypeError,
        match=(
            "456456456456 is an incorrect type: all account and ou id's must be strings not <class 'int'>"  # noqa E501
        ),
    ):
        simple_func()

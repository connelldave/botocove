from datetime import datetime
from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from botocove import CoveSession, cove


@pytest.fixture()
def mock_boto3_session() -> MagicMock:
    mock_session = MagicMock()
    list_accounts_result = {
        "Accounts": [
            {"Id": "123123123123", "Status": "ACTIVE"},
            {"Id": "456456456456", "Status": "ACTIVE"},
        ]
    }
    mock_session.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    describe_account_results = [
        {
            "Account": {
                "Id": "123123123123",
                "Arn": "hello-arn",
                "Email": "email@address.com",
                "Name": "an-account-name",
                "Status": "ACTIVE",
                "JoinedMethod": "CREATED",
                "JoinedTimestamp": datetime(2015, 1, 1),
            }
        },
        {
            "Account": {
                "Id": "456456456456",
                "Arn": "hello-arn",
                "Email": "email@address.com",
                "Name": "an-account-name",
                "Status": "ACTIVE",
                "JoinedMethod": "CREATED",
                "JoinedTimestamp": datetime(2015, 1, 1),
            }
        },
    ]
    mock_session.client.return_value.describe_account.side_effect = (
        describe_account_results
    )
    return mock_session


def test_decorated_simple_func(mock_boto3_session: MagicMock) -> None:
    @cove(assuming_session=mock_boto3_session)
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output["Results"]) == 2


def test_empty_target_ids(mock_boto3_session: MagicMock) -> None:
    @cove(assuming_session=mock_boto3_session, target_ids=[])
    def simple_func(session: CoveSession) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match="There are no eligible account ids to run decorated func against",  # noqa: E501
    ):
        simple_func()


def test_ignore_ids(mock_boto3_session: MagicMock) -> None:
    @cove(assuming_session=mock_boto3_session, ignore_ids=["123123123123"])
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, one ignored.
    # simple_func calls == one mock AWS accounts
    assert len(cove_output["Results"]) == 1


def test_target_and_ignore_ids(mock_boto3_session: MagicMock) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["123123123123", "456456456456"],
        ignore_ids=["456456456456"],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, two in targets, one of which is ignored.
    # simple_func calls == one target AWS accounts
    assert len(cove_output["Results"]) == 1


def test_empty_ignore_ids(mock_boto3_session: MagicMock) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["123123123123", "456456456456"],
        ignore_ids=[],
    )
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, four in targets
    # simple_func calls == two targeted AWS accounts
    print(cove_output)
    assert len(cove_output["Results"]) == 2


def test_decorated_simple_func_passed_args(mock_boto3_session: MagicMock) -> None:
    @cove(assuming_session=mock_boto3_session, ignore_ids=["456456456456"])
    def simple_func(session: CoveSession, arg1: int, arg2: int, arg3: int) -> int:
        return arg1 + arg2 + arg3

    cove_output = simple_func(1, 2, 3)
    expected = [
        {
            "Id": "123123123123",
            "Arn": "hello-arn",
            "Email": "email@address.com",
            "Name": "an-account-name",
            "Status": "ACTIVE",
            "AssumeRoleSuccess": True,
            "Result": 6,
            "RoleName": "OrganizationAccountAccessRole",
            "RoleSessionName": "OrganizationAccountAccessRole",
        }
    ]
    # Two simple_func calls == two mock AWS accounts
    assert cove_output["Results"] == expected


def test_decorated_simple_func_passed_session_name(
    mock_boto3_session: MagicMock,
) -> None:
    session_name = "testSessionName"

    @cove(
        assuming_session=mock_boto3_session,
        role_session_name=session_name,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[str]:
        return session.session_information["RoleSessionName"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_name for x in cove_output["Results"])


def test_decorated_simple_func_passed_policy(mock_boto3_session: MagicMock) -> None:
    session_policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'  # noqa: E501

    @cove(
        assuming_session=mock_boto3_session,
        policy=session_policy,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[str]:
        return session.session_information["Policy"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_policy for x in cove_output["Results"])


def test_decorated_simple_func_passed_policy_arn(mock_boto3_session: MagicMock) -> None:
    session_policy_arns = ["arn:aws:iam::aws:policy/IAMReadOnlyAccess"]

    @cove(
        assuming_session=mock_boto3_session,
        policy_arns=session_policy_arns,
        org_master=False,
    )
    def simple_func(session: CoveSession) -> Optional[List[str]]:
        return session.session_information["PolicyArns"]

    cove_output = simple_func()

    assert cove_output["Exceptions"] == []
    assert all(x["Result"] == session_policy_arns for x in cove_output["Results"])

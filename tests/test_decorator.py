from unittest.mock import MagicMock

import pytest

from botocove import cove


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
        {"Account": {"Id": "123123123123"}},
        {"Account": {"Id": "456456456456"}},
    ]
    mock_session.client.return_value.describe_account.side_effect = (
        describe_account_results
    )
    return mock_session


def test_decorated_simple_func(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session)
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output["Results"]) == 2


def test_target_ids(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, target_ids=["1"])
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # One account in target_ids, two in mock response.
    # simple_func calls == one mock AWS accounts
    assert len(cove_output["Results"]) == 1


def test_empty_target_ids(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, target_ids=[])
    def simple_func(session) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match="There are no eligible account ids to run decorated func simple_func against",  # noqa: E501
    ):
        simple_func()


def test_ignore_ids(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, ignore_ids=["123123123123"])
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, one ignored.
    # simple_func calls == one mock AWS accounts
    assert len(cove_output["Results"]) == 1


def test_target_and_ignore_ids(mock_boto3_session) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["123123123123", "456456456456"],
        ignore_ids=["456456456456"],
    )
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, two in targets, one of which is ignored.
    # simple_func calls == one target AWS accounts
    assert len(cove_output["Results"]) == 1


def test_empty_ignore_ids(mock_boto3_session) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["123123123123", "456456456456"],
        ignore_ids=[],
    )
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, four in targets
    # simple_func calls == two targeted AWS accounts
    print(cove_output)
    assert len(cove_output["Results"]) == 2


def test_decorated_simple_func_passed_args(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, ignore_ids=["456456456456"])
    def simple_func(session, arg1: int, arg2: int, arg3: int) -> int:
        return arg1 + arg2 + arg3

    cove_output = simple_func(1, 2, 3)
    expected = [{"Id": "123123123123", "AssumeRoleSuccess": True, "Result": 6}]
    # Two simple_func calls == two mock AWS accounts
    assert cove_output["Results"] == expected

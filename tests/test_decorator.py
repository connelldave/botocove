from unittest.mock import MagicMock

import pytest

from botocove import cove


@pytest.fixture()
def mock_boto3_session() -> MagicMock:
    mock_session = MagicMock()
    list_accounts_result = {
        "Accounts": [
            {"Id": "12345689012", "Status": "ACTIVE"},
            {"Id": "12345689013", "Status": "ACTIVE"},
        ]
    }
    mock_session.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    # Mock out the credential requiring API call
    return mock_session


def test_decorated_simple_func(mock_boto3_session) -> None:
    @cove(org_session=mock_boto3_session)
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output) == 2


def test_target_ids(mock_boto3_session) -> None:
    @cove(org_session=mock_boto3_session, target_ids=["1"])
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # One account in target_ids, two in mock response.
    # simple_func calls == one mock AWS accounts
    assert len(cove_output) == 1


def test_ignore_ids(mock_boto3_session) -> None:
    @cove(org_session=mock_boto3_session, ignore_ids=["12345689012"])
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, one ignored.
    # simple_func calls == one mock AWS accounts
    assert len(cove_output) == 1


def test_target_and_ignore_ids(mock_boto3_session) -> None:
    @cove(
        org_session=mock_boto3_session,
        target_ids=["1", "2", "3", "4"],
        ignore_ids=["4"],
    )
    def simple_func(session) -> str:
        return "hello"

    cove_output = simple_func()
    # Two in mock response, four in targets, one of which is ignored.
    # simple_func calls == three targeted AWS accounts
    assert len(cove_output) == 3


def test_no_account_exception(mock_boto3_session) -> None:
    @cove(
        org_session=mock_boto3_session,
        target_ids=["1"],
        ignore_ids=["1"],
    )
    def simple_func(session) -> str:
        return "hello"

    with pytest.raises(
        ValueError, match="No accounts are accessible: check logs for detail"
    ):
        simple_func()


def test_decorated_simple_func_passed_args(mock_boto3_session) -> None:
    @cove(org_session=mock_boto3_session)
    def simple_func(session, arg1, arg2, arg3) -> str:
        return arg1 + arg2 + arg3

    cove_output = simple_func(1, 2, 3)
    # Two simple_func calls == two mock AWS accounts
    assert cove_output == [6, 6]

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from botocove import cove


@pytest.fixture()
def mock_boto3_session() -> MagicMock:
    mock_session = MagicMock()
    list_accounts_result = {
        "Accounts": [
            {"Id": "123123123123", "Status": "ACTIVE"},
            {"Id": "123123123123", "Status": "ACTIVE"},
        ]
    }
    mock_session.client.return_value.get_paginator.return_value.paginate.return_value.build_full_result.return_value = (  # noqa E501
        list_accounts_result
    )
    describe_account_results = [
        {"Account": {"Id": "123"}},
        {"Account": {"Id": "456"}},
    ]
    mock_session.client.return_value.describe_account.side_effect = (
        describe_account_results
    )
    # Mock out the credential requiring API call
    return mock_session


def test_no_account_id_exception(mock_boto3_session) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["456456456456"],
        ignore_ids=["456456456456"],
    )
    def simple_func(session) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match=(
            "There are no eligible account ids to run "
            "decorated func simple_func against"
        ),
    ):
        simple_func()


def test_no_valid_sessions_exception(mock_boto3_session) -> None:
    mock_boto3_session.client.return_value.assume_role.side_effect = [
        ClientError({"Error": {}}, "error1"),
        ClientError({"Error": {}}, "error2"),
    ]

    @cove(assuming_session=mock_boto3_session, target_ids=["123", "456"])
    def simple_func(session) -> str:
        return "hello"

    with pytest.raises(
        ValueError,
        match=("No accounts are accessible: check logs for detail"),
    ):
        simple_func()


def test_handled_exception_in_wrapped_func(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, target_ids=["123"])
    def simple_func(session) -> str:
        raise Exception("oh no")
        return "hello"

    results = simple_func()
    # Compare repr of exceptions
    assert repr(results["Exceptions"]) == repr(
        [
            {
                "Id": "123",
                "AssumeRoleSuccess": True,
                "ExceptionDetails": [Exception("oh no")],
            }
        ]
    )


def test_raised_exception_in_wrapped_func(mock_boto3_session) -> None:
    @cove(assuming_session=mock_boto3_session, target_ids=["123"], raise_exception=True)
    def simple_func(session) -> None:
        raise Exception("oh no")

    with pytest.raises(Exception, match="oh no"):
        simple_func()


def test_malformed_ignore_ids(mock_boto3_session) -> None:
    @cove(
        assuming_session=mock_boto3_session,
        target_ids=["456456456456"],
        ignore_ids=["cat"],
    )
    def simple_func(session) -> str:
        return "hello"

    with pytest.raises(
        TypeError,
        match=("All ignore_id in list must be 12 character strings"),
    ):
        simple_func()

import functools

import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3.session import Session

from botocove import cove
from tests.moto_mock_org.moto_models import SmallOrg

cove = functools.partial(cove, thread_workers=1, raise_exception=True)


@pytest.fixture(autouse=True)
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


@pytest.fixture(autouse=True)
def _mock_small_org(mock_small_org: SmallOrg) -> None:
    pass


def _query_region(session: Session) -> str:
    response = session.client("ec2").describe_availability_zones()
    return response["AvailabilityZones"][0]["RegionName"]


def test_when_region_is_unspecified_then_result_has_no_region_key() -> None:
    output = cove(_query_region)()
    assert output["Results"]
    for result in output["Results"]:
        assert "Region" not in result


def test_when_region_is_unspecified_then_output_has_one_result_per_account(
    mock_session: Session,
) -> None:
    output = cove(_query_region)()
    assert len(output["Results"]) == _count_member_accounts(mock_session)


def test_when_region_is_str_then_raises_type_error() -> None:
    with pytest.raises(
        TypeError, match=r"regions must be a list of str\. Got str 'eu-west-1'\."
    ):
        cove(_query_region, regions="eu-west-1")()  # type: ignore[arg-type]


def test_when_region_is_empty_then_raises_value_error() -> None:
    with pytest.raises(
        ValueError, match=r"regions must have at least 1 element\. Got \[\]\."
    ):
        cove(_query_region, regions=[])()


def test_when_any_region_is_passed_then_result_has_region_key() -> None:
    output = cove(_query_region, regions=["eu-west-1"])()
    assert output["Results"]
    for result in output["Results"]:
        assert result["Region"] == "eu-west-1"


def test_when_two_regions_are_passed_then_output_has_one_result_per_account_per_region(
    mock_session: Session,
) -> None:

    output = cove(_query_region, regions=["eu-west-1", "us-east-1"])()

    number_of_member_accounts = _count_member_accounts(mock_session)

    for region in ["eu-west-1", "us-east-1"]:
        number_of_results_per_region = sum(
            1 for result in output["Results"] if result["Region"] == region
        )
        assert number_of_results_per_region == number_of_member_accounts


def _count_member_accounts(session: Session) -> int:
    client = session.client("organizations")
    pages = client.get_paginator("list_accounts").paginate()
    number_of_member_accounts = sum(1 for page in pages for _ in page["Accounts"]) - 1
    return number_of_member_accounts

from botocore.exceptions import EndpointConnectionError
from typing import Any
import pytest
from boto3.session import Session

from botocove import cove, InvalidRegion
from tests.moto_mock_org.moto_models import SmallOrg


def test_when_region_is_unspecified_then_result_has_no_region_key(
    mock_small_org: SmallOrg,
) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    assert output["Results"]
    for result in output["Results"]:
        assert "Region" not in result


def test_when_region_is_unspecified_then_output_has_one_result_per_account(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    print(output["Results"])
    print(len(output["Results"]))
    print(_count_member_accounts(mock_session))
    print(mock_small_org.all_accounts)
    assert len(output["Results"]) == _count_member_accounts(mock_session)


def test_when_region_is_str_then_raises_type_error(mock_small_org: SmallOrg) -> None:
    @cove(regions="eu-west-1")  # type: ignore[arg-type]
    def do_nothing() -> None:
        pass

    with pytest.raises(
        TypeError, match=r"regions must be a list of str\. Got str 'eu-west-1'\."
    ):
        do_nothing()


def test_when_region_is_empty_then_raises_value_error(mock_small_org: SmallOrg) -> None:
    @cove(regions=[])
    def do_nothing() -> None:
        pass

    with pytest.raises(
        ValueError, match=r"regions must have at least 1 element\. Got \[\]\."
    ):
        do_nothing()


def test_when_any_region_is_passed_then_result_has_region_key(
    mock_small_org: SmallOrg,
) -> None:
    @cove(regions=["eu-west-1"])
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    assert output["Results"]
    for result in output["Results"]:
        assert result["Region"] == "eu-west-1"


def test_when_two_regions_are_passed_then_output_has_one_result_per_account_per_region(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["eu-west-1", "us-east-1"])
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()

    number_of_member_accounts = _count_member_accounts(mock_session)

    for region in ["eu-west-1", "us-east-1"]:
        number_of_results_per_region = sum(
            1 for result in output["Results"] if result["Region"] == region
        )
        assert number_of_results_per_region == number_of_member_accounts


def test_moto_when_region_is_invalid_and_client_does_nothing_then_output_has_result(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["xxxx"])
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()

    assert output["Results"]
    for result in output["Results"]:
        assert result["Region"] == "xxxx"


def test_moto_when_region_is_invalid_and_client_calls_api_then_raises_endpoint_error(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    # Moto's FAQ says it "only allows valid regions, supporting the same regions
    # that AWS supports" [1]. But it's not true for all service backends.
    #
    # Normally I would use the STS GetCallerIdentity API as the simplest call.
    # But Moto's STS backend doesn't seem to trigger the error. The EC2
    # DescribeAvailabilityZones API does trigger the error.
    #
    # [1]: https://github.com/getmoto/moto/blob/7b982522144e3f75e936560e76a92a798fe4e0fd/docs/docs/faq.rst
    @cove(regions=["xxxx"])
    def call_api(session: Session) -> Any:
        return session.client("ec2").describe_availability_zones()

    with pytest.raises(InvalidRegion, match=f"^xxxx$"):
        call_api()


def _count_member_accounts(session: Session) -> int:
    client = session.client("organizations")
    pages = client.get_paginator("list_accounts").paginate()
    number_of_member_accounts = sum(1 for page in pages for _ in page["Accounts"]) - 1
    return number_of_member_accounts

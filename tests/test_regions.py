from typing import Any

import pytest
from boto3.session import Session
from botocore.exceptions import EndpointConnectionError

from botocove import cove
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


warning_pattern = (
    r"^Unrecognized region may cause connection error. Check spelling of `.*?`\.$"
)


def test_when_region_is_misspelled_then_cove_warns_user_to_check_spelling(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["us-esat-1"])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.warns(UserWarning, match=warning_pattern) as recwarn:
        do_nothing()
        assert len(recwarn) == 1
        assert "us-esat-1" in str(recwarn.list[0].message)


def test_when_two_regions_are_misspelled_then_cove_warns_to_check_spelling_of_each(
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["us-esat-1", "ap-norhteast-2"])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.warns(UserWarning, match=warning_pattern) as recwarn:
        do_nothing()
        assert len(recwarn) == 2
        assert "us-esat-1" in str(recwarn.list[0].message)
        assert "ap-norhteast-2" in str(recwarn.list[1].message)


@pytest.mark.filterwarnings(f"ignore:{warning_pattern}:UserWarning")
def test_when_misspelling_region_and_raising_exceptions_then_cove_raises_endpoint_connection_error(  # noqa: E501
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["us-esat-1"], raise_exception=True)
    def call_an_api(session: Session) -> Any:
        # Moto's FAQ says it "only allows valid regions, supporting the same regions
        # that AWS supports" [1]. But it's not true for all service backends.
        #
        # Normally I would use the STS GetCallerIdentity API as the simplest call.
        # But Moto's STS backend doesn't seem to trigger the error. The EC2
        # DescribeAvailabilityZones API does trigger the error.
        #
        # [1]: https://github.com/getmoto/moto/blob/7b982522144e3f75e936560e76a92a798fe4e0fd/docs/docs/faq.rst  # noqa: E501
        return session.client("ec2").describe_availability_zones()

    pattern = (
        r'Could not connect to the endpoint URL: "https://ec2.us-esat-1.amazonaws.com/"'
    )
    with pytest.raises(EndpointConnectionError, match=pattern):
        call_an_api()


@pytest.mark.filterwarnings(f"ignore:{warning_pattern}:UserWarning")
def test_when_misspelling_region_and_catching_exceptions_then_cove_output_has_endpoint_connection_error(  # noqa: E501
    mock_session: Session, mock_small_org: SmallOrg
) -> None:
    @cove(regions=["us-esat-1"])
    def call_an_api(session: Session) -> Any:
        return session.client("ec2").describe_availability_zones()

    pattern = (
        r'Could not connect to the endpoint URL: "https://ec2.us-esat-1.amazonaws.com/"'
    )
    output = call_an_api()
    assert output.get("Results") == []
    assert output["Exceptions"]
    for result in output["Exceptions"]:
        assert result["Region"] == "us-esat-1"
        assert isinstance(result["ExceptionDetails"], EndpointConnectionError)
        assert str(result["ExceptionDetails"]) == pattern


def _count_member_accounts(session: Session) -> int:
    client = session.client("organizations")
    pages = client.get_paginator("list_accounts").paginate()
    number_of_member_accounts = sum(1 for page in pages for _ in page["Accounts"]) - 1
    return number_of_member_accounts

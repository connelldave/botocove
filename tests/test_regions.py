import pytest
from boto3.session import Session

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
    assert len(output["Results"]) == _count_member_accounts(mock_session)


def test_when_region_is_str_then_raises_type_error(mock_small_org: SmallOrg) -> None:
    @cove(regions="eu-west-1")  # type: ignore[arg-type]
    def do_nothing() -> None:
        pass

    with pytest.raises(
        TypeError, match=r"regions must be a list of str\. Got str 'eu-west-1'\."
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


def _count_member_accounts(session: Session) -> int:
    client = session.client("organizations")
    pages = client.get_paginator("list_accounts").paginate()
    number_of_member_accounts = sum(1 for page in pages for _ in page["Accounts"]) - 1
    return number_of_member_accounts

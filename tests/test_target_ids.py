import pytest
from boto3.session import Session

from botocove import cove
from tests.moto_mock_org.moto_models import SmallOrg


def test_when_unspecified_then_output_has_a_result_for_each_org_account(
    mock_small_org: SmallOrg,
) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    assert set(mock_small_org.all_accounts) == {r["Id"] for r in output["Results"]}


def test_when_account_not_in_org_raises_value_error(
    mock_small_org: SmallOrg,
) -> None:
    account_not_in_org = "111111111111"
    assert account_not_in_org not in mock_small_org.all_accounts

    @cove(target_ids=[account_not_in_org])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError, match=r"Account 111111111111 is not in the organization\."
    ):
        do_nothing()


def test_when_empty_sequence_raises_value_error(
    mock_small_org: SmallOrg,
) -> None:
    @cove(target_ids=[])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError, match=r"target_ids when specified must have at least 1 element\."
    ):
        do_nothing()

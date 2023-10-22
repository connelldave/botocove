import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3.session import Session

from botocove import cove
from tests.moto_mock_org.moto_models import SmallOrg


@pytest.fixture(autouse=True)
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


def test_when_unspecified_then_output_has_a_result_for_each_org_account(
    mock_small_org: SmallOrg,
) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    assert set(mock_small_org.all_accounts) == {r["Id"] for r in output["Results"]}


def test_when_accounts_in_org_then_output_has_result_for_each_target_id(
    mock_small_org: SmallOrg,
) -> None:
    some_org_accounts = [
        mock_small_org.all_accounts[0],
        mock_small_org.all_accounts[1],
    ]

    @cove(target_ids=some_org_accounts)
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()
    assert set(some_org_accounts) == {r["Id"] for r in output["Results"]}


def test_when_target_id_is_str_then_raises_type_error(mock_small_org: SmallOrg) -> None:
    @cove(target_ids="111111111111")  # type: ignore[arg-type]
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        TypeError, match=r"target_ids must be a list of str. Got str '111111111111'\."
    ):
        do_nothing()


def test_when_account_not_in_org_raises_value_error(
    mock_small_org: SmallOrg,
) -> None:
    account_not_in_org = "111111111111"
    assert account_not_in_org not in mock_small_org.all_accounts

    @cove(target_ids=[account_not_in_org])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError, match=r"Account 111111111111 is not ACTIVE in the organization\."
    ):
        do_nothing()


def test_when_empty_sequence_raises_value_error(
    mock_small_org: SmallOrg,
) -> None:
    @cove(target_ids=[])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError, match=r"target_ids must have at least 1 element\. Got \[\]\."
    ):
        do_nothing()

# test_new.py - I don't know what to call this yet.
import pytest
from boto3.session import Session

from botocove import cove


def test_when_org_not_used_and_has_target_account_then_output_has_id_key(
    mock_session: Session,
) -> None:
    @cove(target_ids=["111111111111"])
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()

    result_ids = [r["Id"] for r in output["Results"]]
    assert result_ids == ["111111111111"]


def test_when_org_not_used_and_target_account_passed_then_output_has_no_org_metadata(
    mock_session: Session,
) -> None:
    @cove(target_ids=["111111111111"])
    def do_nothing(session: Session) -> None:
        pass

    output = do_nothing()

    org_metadata_keys = {"Name", "Arn", "Email", "Status", "JoinedDate"}
    assert output["Results"]
    for r in output["Results"]:
        for k in r:
            assert k not in org_metadata_keys


def test_when_org_not_used_and_has_no_target_then_raise_value_error(
    mock_session: Session,
) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError,
        match="There are no eligible account ids to run decorated func against",
    ):
        do_nothing()


def test_when_org_not_used_and_has_target_ou_then_raise_value_error(
    mock_session: Session,
) -> None:
    @cove(target_ids=["ou-aaaa-aaaaaaaa"])
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        ValueError, match="provided id is not an aws account: ou-aaaa-aaaaaaaa"
    ):
        do_nothing()

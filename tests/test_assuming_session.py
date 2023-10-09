import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3.session import Session
from botocore.exceptions import NoRegionError

from botocove import cove
from tests.moto_mock_org.moto_models import SmallOrg


@pytest.fixture()
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


def _call_regional_api(session: Session) -> str:
    session.client("sqs").list_queues()
    return "OK"


def test_when_no_assuming_session_and_no_default_region_then_cove_raises_error(
    mock_small_org: SmallOrg,
) -> None:
    output = cove(_call_regional_api)()

    assert not output["Results"]
    assert not output["FailedAssumeRole"]
    assert output["Exceptions"]
    for error in output["Exceptions"]:
        assert isinstance(error["ExceptionDetails"], NoRegionError)


@pytest.mark.xfail()
@pytest.mark.usefixtures("_default_region")
def test_when_no_assuming_session_and_default_region_then_cove_gives_result(
    mock_small_org: SmallOrg,
) -> None:
    output = cove(_call_regional_api)()

    assert not output["Exceptions"]
    assert not output["FailedAssumeRole"]
    assert output["Results"]


@pytest.mark.xfail()
def test_when_assuming_session_has_region_and_no_default_region_then_cove_gives_result(
    mock_small_org: SmallOrg,
) -> None:
    output = cove(
        _call_regional_api, assuming_session=Session(region_name="eu-west-1")
    )()

    assert not output["Exceptions"]
    assert not output["FailedAssumeRole"]
    assert output["Results"]

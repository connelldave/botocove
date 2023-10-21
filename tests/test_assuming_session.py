import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3.session import Session
from botocore.exceptions import NoRegionError
from moto import mock_sqs

from botocove import cove

# Each test calls a regional API and with a different configuration for the
# assuming session and environment variables. The content of the successful
# response doesn't matter. What matters is whether the request succeeds or
# fails. To make the assertions easier all `cove` calls set `raise_exception`.


def _call_regional_api(session: Session) -> str:
    with mock_sqs():
        session.client("sqs").list_queues()
        return "OK"


@pytest.fixture(autouse=True)
def _org_with_one_member(mock_session: Session) -> None:
    org_client = mock_session.client("organizations")
    org_client.create_organization(FeatureSet="ALL")
    org_client.create_account(Email="account1@aws.com", AccountName="Account 1")


@pytest.fixture()
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


def test_when_no_assuming_session_and_no_default_region_then_cove_raises_error() -> None:  # noqa: 501
    with pytest.raises(NoRegionError, match=r"^You must specify a region\.$"):
        cove(_call_regional_api, raise_exception=True)()


@pytest.mark.usefixtures("_default_region")
def test_when_no_assuming_session_and_default_region_then_cove_gives_result() -> None:
    output = cove(_call_regional_api, raise_exception=True)()
    assert output["Results"][0]["Result"] == "OK"


def test_when_assuming_session_has_region_and_no_default_region_then_cove_gives_result() -> None:  # noqa: 501
    output = cove(
        _call_regional_api,
        assuming_session=Session(region_name="eu-west-1"),
        raise_exception=True,
    )()
    assert output["Results"][0]["Result"] == "OK"

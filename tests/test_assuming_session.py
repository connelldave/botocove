import pytest
from _pytest.monkeypatch import MonkeyPatch
from boto3.session import Session
from botocore.exceptions import NoRegionError
from moto import mock_ec2

from botocove import cove

# Query the region with different configurations of assuming session and
# environment variables. To make the assertions easier all `cove` calls set
# `raise_exception`. If set the assuming session region and the default region
# are always distinct to be able to assert the source of the query result.


def _query_region(session: Session) -> str:
    with mock_ec2():
        response = session.client("ec2").describe_availability_zones()
        return response["AvailabilityZones"][0]["RegionName"]


@pytest.fixture(autouse=True)
def _org_with_one_member(mock_session: Session) -> None:
    org_client = mock_session.client("organizations")
    org_client.create_organization(FeatureSet="ALL")
    org_client.create_account(Email="account1@aws.com", AccountName="Account 1")


@pytest.fixture()
def _default_region(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


def test_when_no_assuming_session_and_no_default_region_then_cove_raises_error() -> (
    None
):
    with pytest.raises(NoRegionError, match=r"^You must specify a region\.$"):
        cove(_query_region, raise_exception=True)()


@pytest.mark.usefixtures("_default_region")
def test_when_no_assuming_session_then_cove_uses_default_region() -> None:
    output = cove(_query_region, raise_exception=True)()
    assert output["Results"][0]["Result"] == "eu-west-1"


def test_when_no_default_region_then_cove_uses_assuming_session_region() -> None:
    output = cove(
        _query_region,
        assuming_session=Session(region_name="eu-central-1"),
        raise_exception=True,
    )()
    assert output["Results"][0]["Result"] == "eu-central-1"

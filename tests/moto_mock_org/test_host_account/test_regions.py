from botocove.cove_host_account import CoveHostAccount
from tests.moto_mock_org.moto_models import SmallOrg


def test_regions(mock_small_org: SmallOrg) -> None:

    host_account = CoveHostAccount(
        target_ids=None,
        ignore_ids=None,
        rolename=None,
        role_session_name=None,
        policy=None,
        policy_arns=None,
        org_master=True,
        assuming_session=None,
        regions=["eu-west-1", "eu-west-2"],
        thread_workers=20,
    )
    sessions = host_account.get_cove_sessions()
    account_ids = [acc_id["Id"] for acc_id in sessions]
    assert len(account_ids) == len(host_account.target_accounts) * 2

    regions = [acc_id["Region"] for acc_id in sessions]
    assert "eu-west-1" in regions
    assert "eu-west-2" in regions


def test_no_regions(mock_small_org: SmallOrg) -> None:

    host_account = CoveHostAccount(
        target_ids=None,
        ignore_ids=None,
        rolename=None,
        role_session_name=None,
        policy=None,
        policy_arns=None,
        org_master=True,
        assuming_session=None,
        regions=None,
        thread_workers=20,
    )
    sessions = host_account.get_cove_sessions()
    account_ids = [acc_id["Id"] for acc_id in sessions]
    assert set(account_ids) == set(mock_small_org.all_accounts)

    for s in sessions:
        assert s.get("Region", None) is None

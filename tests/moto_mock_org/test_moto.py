from botocove.cove_host_account import CoveHostAccount
from tests.moto_mock_org.moto_models import LargeOrg, SmallOrg


def test_small_org(mock_small_org: SmallOrg) -> None:
    host_account = CoveHostAccount(
        target_ids=None,
        ignore_ids=None,
        rolename=None,
        role_session_name=None,
        policy=None,
        policy_arns=None,
        external_id=None,
        assuming_session=None,
        regions=None,
        thread_workers=20,
    )
    assert mock_small_org.master_acc_id == host_account.host_account_id
    assert set(mock_small_org.all_accounts) == host_account.target_accounts


def test_large_org(mock_large_org: LargeOrg) -> None:

    host_account = CoveHostAccount(
        target_ids=None,
        ignore_ids=None,
        rolename=None,
        role_session_name=None,
        policy=None,
        policy_arns=None,
        external_id=None,
        assuming_session=None,
        regions=None,
        thread_workers=20,
    )
    assert mock_large_org.master_acc_id == host_account.host_account_id
    assert set(mock_large_org.all_accounts) == host_account.target_accounts

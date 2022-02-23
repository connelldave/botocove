from botocove.cove_host_account import CoveHostAccount
from tests.moto_mock_org.moto_models import SmallOrg


def test_target_all_in_org(mock_small_org: SmallOrg) -> None:

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
    assert mock_small_org.master_acc_id not in account_ids


def test_target_all_in_org_ignore_one(mock_small_org: SmallOrg) -> None:

    ignore_acc = mock_small_org.all_accounts[0]

    host_account = CoveHostAccount(
        target_ids=None,
        ignore_ids=[ignore_acc],
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

    assert set(account_ids) == set(mock_small_org.all_accounts[1:])
    assert ignore_acc not in account_ids


def test_target_targets_and_ignores(mock_small_org: SmallOrg) -> None:

    target_accs = mock_small_org.all_accounts[1:]
    ignore_acc = mock_small_org.all_accounts[0]

    host_account = CoveHostAccount(
        target_ids=target_accs,
        ignore_ids=[ignore_acc],
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

    assert set(account_ids) == set(mock_small_org.all_accounts[1:])
    assert ignore_acc not in account_ids


def test_target_just_targets(mock_small_org: SmallOrg) -> None:

    target_accs = mock_small_org.all_accounts[0:2]

    host_account = CoveHostAccount(
        target_ids=target_accs,
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

    assert set(account_ids) == set(mock_small_org.all_accounts[0:2])

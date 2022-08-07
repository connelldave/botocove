import logging
import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Set, Union

import boto3
from boto3.session import Session
from botocore.config import Config
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_organizations.type_defs import AccountTypeDef
from mypy_boto3_sts.client import STSClient
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef

from botocove.cove_types import CoveSessionInformation

logger = logging.getLogger(__name__)


DEFAULT_ROLENAME = "OrganizationAccountAccessRole"


class CoveHostAccount(object):
    target_regions: Sequence[Optional[str]]

    def __init__(
        self,
        target_ids: Optional[List[str]],
        ignore_ids: Optional[List[str]],
        rolename: Optional[str],
        role_session_name: Optional[str],
        policy: Optional[str],
        policy_arns: Optional[List[PolicyDescriptorTypeTypeDef]],
        assuming_session: Optional[Session],
        org_master: bool,
        thread_workers: int,
        regions: Optional[List[str]],
    ) -> None:

        self.thread_workers = thread_workers

        # sts_client is no longer used, but it left here in case it is part of
        # the public interface.
        self.sts_client = _get_boto3_sts_client(assuming_session, thread_workers)

        self.host_account_id = _get_host_account_id(assuming_session, thread_workers)

        if regions is None:
            self.target_regions = [None]
        else:
            self.target_regions = regions

        self.provided_ignore_ids = ignore_ids
        self.provided_target_ids = target_ids

        if not org_master and self.provided_target_ids:
            account_map = _map_non_org_accounts(self.provided_target_ids)
        else:
            self.org_client = _get_boto3_org_client(assuming_session, thread_workers)
            account_map = _map_active_accounts(self.org_client)

        self.target_account_map = _resolve_target_accounts(
            self.org_client, account_map, target_ids, ignore_ids, self.host_account_id
        )

        if not self.target_accounts:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )

        self.role_to_assume = rolename or DEFAULT_ROLENAME
        self.role_session_name = role_session_name or self.role_to_assume
        self.policy = policy
        self.policy_arns = policy_arns

        self.org_master = org_master

    def get_cove_sessions(self) -> List[CoveSessionInformation]:
        logger.info(f"Getting session information for {self.target_accounts=}")
        logger.info(f"Role: {self.role_to_assume=} {self.role_session_name=}")
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")
        return list(self._generate_account_sessions())

    def _generate_account_sessions(self) -> Iterable[CoveSessionInformation]:
        for region in self.target_regions:
            for account in self.target_account_map.values():
                account_details: CoveSessionInformation = CoveSessionInformation(
                    Id=account["Id"],
                    RoleName=self.role_to_assume,
                    RoleSessionName=self.role_session_name,
                    Policy=self.policy,
                    PolicyArns=self.policy_arns,
                    AssumeRoleSuccess=False,
                    Region=region,
                    ExceptionDetails=None,
                    Name=account.get("Name"),
                    Arn=account.get("Arn"),
                    Email=account.get("Email"),
                    Status=account.get("Status"),
                    Result=None,
                )
                yield account_details

    # Is target_accounts part of the public interface? I see it used in tests but
    # I don't see why a user would refer to it.
    @property
    def target_accounts(self) -> Set[str]:
        return set(self.target_account_map)


def _resolve_target_accounts(
    client: OrganizationsClient,
    account_map: Dict[str, AccountTypeDef],
    target_ids: Optional[List[str]],
    ignore_ids: Optional[List[str]],
    host_account_id: str,
) -> Dict[str, AccountTypeDef]:

    if target_ids is not None:
        included_accounts = _list_accounts_for_all_resources(client, target_ids)
    else:
        included_accounts = set(account_map)

    if ignore_ids is not None:
        ignored_accounts = _list_accounts_for_all_resources(client, ignore_ids)
    else:
        ignored_accounts = set()

    target_accounts = included_accounts - ignored_accounts - {host_account_id}

    return {
        _id: account for _id, account in account_map.items() if _id in target_accounts
    }


def _list_accounts_for_all_resources(
    client: OrganizationsClient, resource_ids: List[str]
) -> Set[str]:
    accounts: Set[str] = set()
    for res in resource_ids:
        accounts.update(_list_accounts_for_resource(client, res))
    return accounts


def _list_accounts_for_resource(
    client: OrganizationsClient, resource_id: str
) -> Set[str]:
    if _is_account_id(resource_id):
        return {resource_id}
    if _is_organizational_unit_id(resource_id):
        return _list_descendant_accounts(client, resource_id)
    raise ValueError(f"provided id is neither an aws account nor an ou: {resource_id}")


def _is_organizational_unit_id(resource_id: str) -> bool:
    return bool(re.match(r"^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$", resource_id))


def _is_account_id(resource_id: str) -> bool:
    return bool(re.match(r"^\d{12}$", resource_id))


def _list_descendant_accounts(
    client: OrganizationsClient, ancestor_id: str
) -> Set[str]:
    descendant_accounts = _list_accounts_for_parent(client, ancestor_id)

    child_ous = _list_organizational_units_for_parent(client, ancestor_id)

    for ou in child_ous:
        descendant_accounts.update(_list_descendant_accounts(client, ou))

    return descendant_accounts


@lru_cache
def _list_accounts_for_parent(client: OrganizationsClient, parent_id: str) -> Set[str]:
    pages = client.get_paginator("list_accounts_for_parent").paginate(
        ParentId=parent_id
    )

    accounts = {account["Id"] for page in pages for account in page["Accounts"]}

    return accounts


@lru_cache
def _list_organizational_units_for_parent(
    client: OrganizationsClient, parent_id: str
) -> Set[str]:
    pages = client.get_paginator("list_organizational_units_for_parent").paginate(
        ParentId=parent_id
    )

    organizational_units = {
        organizational_unit["Id"]
        for page in pages
        for organizational_unit in page["OrganizationalUnits"]
    }

    return organizational_units


def _map_active_accounts(client: OrganizationsClient) -> Dict[str, AccountTypeDef]:
    pages = client.get_paginator("list_accounts").paginate()

    active_accounts = {
        account["Id"]: account
        for page in pages
        for account in page["Accounts"]
        if account["Status"] == "ACTIVE"
    }

    return active_accounts


def _map_non_org_accounts(account_ids: List[str]) -> Dict[str, AccountTypeDef]:
    """Return a degenerate account map for non-org-accounts. The AccountTypeDef
    dict has only an Id key."""

    return {_id: AccountTypeDef(Id=_id) for _id in account_ids}


def _get_host_account_id(session: Optional[Session], thread_workers: int) -> str:
    # I want to inline the STSClient instantiation by calling client directly.
    # But chcek about the logging because requirements first.
    # Is the client logging output considered part of the public interface?
    # I think we don't need special threading settings in these clients any more.
    # CoveHostAccount is set up in a single thread.
    client = _get_boto3_sts_client(session, thread_workers)
    host_account_id = client.get_caller_identity()["Account"]
    return host_account_id


def _get_boto3_org_client(
    assuming_session: Optional[Session],
    thread_workers: int,
) -> OrganizationsClient:
    client: OrganizationsClient = _get_boto3_client(
        "organizations", assuming_session, thread_workers
    )
    return client


def _get_boto3_sts_client(
    assuming_session: Optional[Session],
    thread_workers: int,
) -> STSClient:
    client: STSClient = _get_boto3_client("sts", assuming_session, thread_workers)
    return client


def _get_boto3_client(
    clientname: Union[Literal["organizations"], Literal["sts"]],
    assuming_session: Optional[Session],
    thread_workers: int,
) -> Any:
    if assuming_session:
        logger.info(f"Using provided Boto3 session {assuming_session}")
        return assuming_session.client(
            service_name=clientname,
            config=Config(max_pool_connections=thread_workers),
        )
    logger.info("No Boto3 session argument: using credential chain")
    return boto3.client(
        service_name=clientname,
        config=Config(max_pool_connections=thread_workers),
    )

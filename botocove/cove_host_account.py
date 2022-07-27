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

        self.sts_client = self._get_boto3_sts_client(assuming_session)
        self.org_client = self._get_boto3_org_client(assuming_session)

        self.host_account_id = self.sts_client.get_caller_identity()["Account"]

        if regions is None:
            self.target_regions = [None]
        else:
            self.target_regions = regions

        self.provided_ignore_ids = ignore_ids
        self.provided_target_ids = target_ids
        self.target_account_map = self._resolve_target_accounts()
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
                    Name=account["Name"],
                    Arn=account["Arn"],
                    Email=account["Email"],
                    Status=account["Status"],
                    Result=None,
                )
                yield account_details

    def _get_boto3_client(
        self,
        clientname: Union[Literal["organizations"], Literal["sts"]],
        assuming_session: Optional[Session],
    ) -> Any:
        if assuming_session:
            logger.info(f"Using provided Boto3 session {assuming_session}")
            return assuming_session.client(
                service_name=clientname,
                config=Config(max_pool_connections=self.thread_workers),
            )
        logger.info("No Boto3 session argument: using credential chain")
        return boto3.client(
            service_name=clientname,
            config=Config(max_pool_connections=self.thread_workers),
        )

    def _get_boto3_org_client(
        self, assuming_session: Optional[Session]
    ) -> OrganizationsClient:
        client: OrganizationsClient = self._get_boto3_client(
            "organizations", assuming_session
        )
        return client

    def _get_boto3_sts_client(self, assuming_session: Optional[Session]) -> STSClient:
        client: STSClient = self._get_boto3_client("sts", assuming_session)
        return client

    @property
    def target_accounts(self) -> Set[str]:
        return set(self.target_account_map)

    def _resolve_target_accounts(self) -> Dict[str, AccountTypeDef]:
        account_map = self._map_active_accounts()

        if self.provided_target_ids is not None:
            included_accounts = self._list_accounts_for_all_resources(
                self.provided_target_ids
            )
        else:
            included_accounts = set(account_map)

        if self.provided_ignore_ids is not None:
            ignored_accounts = self._list_accounts_for_all_resources(
                self.provided_ignore_ids
            )
        else:
            ignored_accounts = set()

        target_accounts = included_accounts - ignored_accounts - {self.host_account_id}

        return {
            _id: account
            for _id, account in account_map.items()
            if _id in target_accounts
        }

    def _list_accounts_for_all_resources(self, resource_ids: List[str]) -> Set[str]:
        accounts: Set[str] = set()
        for res in resource_ids:
            accounts.update(self._list_accounts_for_resource(res))
        return accounts

    def _list_accounts_for_resource(self, resource_id: str) -> Set[str]:
        if self._is_account_id(resource_id):
            return {resource_id}
        if self._is_organizational_unit_id(resource_id):
            return self._list_descendant_accounts(resource_id)
        raise ValueError(
            f"provided id is neither an aws account nor an ou: {resource_id}"
        )

    def _is_organizational_unit_id(self, resource_id: str) -> bool:
        return bool(re.match(r"^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$", resource_id))

    def _is_account_id(self, resource_id: str) -> bool:
        return bool(re.match(r"^\d{12}$", resource_id))

    def _list_descendant_accounts(self, ancestor_id: str) -> Set[str]:
        descendant_accounts = self._list_accounts_for_parent(ancestor_id)

        child_ous = self._list_organizational_units_for_parent(ancestor_id)

        for ou in child_ous:
            descendant_accounts.update(self._list_descendant_accounts(ou))

        return descendant_accounts

    @lru_cache
    def _list_accounts_for_parent(self, parent_id: str) -> Set[str]:
        pages = self.org_client.get_paginator("list_accounts_for_parent").paginate(
            ParentId=parent_id
        )

        accounts = {account["Id"] for page in pages for account in page["Accounts"]}

        return accounts

    @lru_cache
    def _list_organizational_units_for_parent(self, parent_id: str) -> Set[str]:
        pages = self.org_client.get_paginator(
            "list_organizational_units_for_parent"
        ).paginate(ParentId=parent_id)

        organizational_units = {
            organizational_unit["Id"]
            for page in pages
            for organizational_unit in page["OrganizationalUnits"]
        }

        return organizational_units

    def _map_active_accounts(self) -> Dict[str, AccountTypeDef]:
        pages = self.org_client.get_paginator("list_accounts").paginate()

        active_accounts = {
            account["Id"]: account
            for page in pages
            for account in page["Accounts"]
            if account["Status"] == "ACTIVE"
        }

        return active_accounts

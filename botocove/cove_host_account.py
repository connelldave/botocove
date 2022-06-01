import logging
import re
from functools import lru_cache
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

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

        self._account_map = self._resolve_target_accounts(target_ids)

        if not self._account_map:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )

        self.role_to_assume = rolename or DEFAULT_ROLENAME
        self.role_session_name = role_session_name or self.role_to_assume
        self.policy = policy
        self.policy_arns = policy_arns

        self.org_master = org_master

    @property
    def target_accounts(self) -> Set[str]:
        return set(self._account_map)

    def get_cove_sessions(self) -> List[CoveSessionInformation]:
        logger.info(f"Getting session information for {self.target_accounts=}")
        logger.info(f"Role: {self.role_to_assume=} {self.role_session_name=}")
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")
        return list(self._generate_account_sessions())

    def _generate_account_sessions(self) -> Iterable[CoveSessionInformation]:
        for region in self.target_regions:
            for account in self._account_map.values():
                account_details = CoveSessionInformation(
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

    def _resolve_target_accounts(
        self, target_ids: Optional[List[str]]
    ) -> Dict[str, AccountTypeDef]:
        accounts_to_ignore = self._gather_ignored_accounts()
        logger.info(f"Ignoring account IDs: {accounts_to_ignore=}")
        accounts_to_target = self._gather_target_accounts(target_ids)

        final_accounts = {
            a["Id"]: self._ensure_complete_account_description(a)
            for a in accounts_to_target
            if a["Id"] not in accounts_to_ignore
        }

        if len(final_accounts) < 1:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )

        return final_accounts

    def _ensure_complete_account_description(
        self, account: AccountTypeDef
    ) -> AccountTypeDef:
        """If the description has only an ID, then the account was probably
        gathered from an account ID in the target_ids list. In this case, return
        a new complete account description. Otherwise assume the description is
        complete and return the input account.
        """

        if list(account.keys()) == ["Id"]:
            logger.info(f"Describing incomplete account {account['Id']}")
            desc = self.org_client.describe_account(AccountId=account["Id"])
            return desc["Account"]
        return account

    def _gather_ignored_accounts(self) -> Set[str]:
        ignored_accounts = {self.host_account_id}

        if self.provided_ignore_ids:
            accs, ous = self._get_validated_ids(self.provided_ignore_ids)
            ignored_accounts.update(accs)
            if ous:
                accs_from_ous = self._get_all_accounts_by_organization_units(ous)
                ignored_accounts.update(a["Id"] for a in accs_from_ous)

        return ignored_accounts

    def _gather_target_accounts(
        self, targets: Optional[List[str]]
    ) -> List[AccountTypeDef]:
        if targets:
            accs, ous = self._get_validated_ids(targets)
            target_accounts: List[AccountTypeDef] = [{"Id": a} for a in accs]
            if ous:
                accs_from_ous = self._get_all_accounts_by_organization_units(ous)
                target_accounts.extend(accs_from_ous)
            return target_accounts
        else:
            # No target_ids passed, getting all accounts in org
            return self._get_active_org_accounts()

    def _get_validated_ids(self, ids: List[str]) -> Tuple[List[str], List[str]]:

        accounts: List[str] = []
        ous: List[str] = []

        for current_id in ids:
            if not isinstance(current_id, str):
                raise TypeError(
                    f"{current_id} is an incorrect type: all account and ou id's must be strings not {type(current_id)}"  # noqa E501
                )
            if re.match(r"^\d{12}$", current_id):
                accounts.append(current_id)
                continue
            if re.match(r"^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$", current_id):
                ous.append(current_id)
                continue
            raise ValueError(
                f"provided id is neither an aws account nor an ou: {current_id}"
            )

        return accounts, ous

    def _get_all_accounts_by_organization_units(
        self, target_ous: List[str]
    ) -> List[AccountTypeDef]:

        account_list: List[AccountTypeDef] = []

        for parent_ou in target_ous:

            current_ou_list: List[str] = []

            # current_ou_list is mutated and recursivly populated with all childs
            self._get_all_child_ous(parent_ou, current_ou_list)

            # for complete list add parent ou as well to list of child ous
            current_ou_list.append(parent_ou)

            account_list.extend(
                self._get_accounts_by_organization_units(current_ou_list)
            )

        return account_list

    def _get_all_child_ous(self, parent_ou: str, ou_list: List[str]) -> None:
        """Depth-first recursion mutates the current_ou_list present in the calling
        function to establish all children of a parent OU"""
        child_ous = self._get_child_ous(parent_ou)
        ou_list.extend(child_ous)

        for ou in child_ous:
            self._get_all_child_ous(ou, ou_list)

    def _get_accounts_by_organization_units(
        self, organization_units: List[str]
    ) -> List[AccountTypeDef]:

        account_list: List[AccountTypeDef] = []

        for ou in organization_units:
            ou_children = self._get_child_accounts(ou)
            account_list.extend(ou_children)

        return account_list

    def _get_active_org_accounts(self) -> List[AccountTypeDef]:
        pages = self.org_client.get_paginator("list_accounts").paginate()
        return [
            account
            for page in pages
            for account in page["Accounts"]
            if account["Status"] == "ACTIVE"
        ]

    @lru_cache()
    def _get_child_ous(self, parent_ou: str) -> List[str]:
        pages = self.org_client.get_paginator(
            "list_organizational_units_for_parent"
        ).paginate(ParentId=parent_ou)
        return [ou["Id"] for page in pages for ou in page["OrganizationalUnits"]]

    @lru_cache()
    def _get_child_accounts(self, parent_ou: str) -> List[AccountTypeDef]:
        pages = self.org_client.get_paginator("list_accounts_for_parent").paginate(
            ParentId=parent_ou
        )
        return [account for page in pages for account in page["Accounts"]]

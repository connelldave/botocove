import logging
import re
from typing import Any, List, Literal, Optional, Set, Tuple, Union

import boto3
from boto3.session import Session
from botocore.config import Config
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_sts.client import STSClient

from botocove.cove_types import CoveSessionInformation

logger = logging.getLogger(__name__)


DEFAULT_ROLENAME = "OrganizationAccountAccessRole"


class CoveHostAccount(object):
    def __init__(
        self,
        target_ids: Optional[List[str]],
        ignore_ids: Optional[List[str]],
        rolename: Optional[str],
        role_session_name: Optional[str],
        policy: Optional[str],
        policy_arns: Optional[List[str]],
        assuming_session: Optional[Session],
        org_master: bool,
    ) -> None:

        self.sts_client = self._get_boto3_sts_client(assuming_session)
        self.org_client = self._get_boto3_org_client(assuming_session)

        self.provided_ignore_ids = ignore_ids
        self.target_accounts = self._resolve_target_accounts(target_ids)
        if not self.target_accounts:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )

        self.role_to_assume = rolename or DEFAULT_ROLENAME
        self.role_session_name = role_session_name or self.role_to_assume
        self.policy = policy
        self.policy_arns = policy_arns

        self.org_master = org_master

    def get_cove_session_info(self) -> List[CoveSessionInformation]:
        logger.info(
            f"Getting session information: {self.role_to_assume=} "
            f"{self.role_session_name=} {self.target_accounts=} "
            f"{self.provided_ignore_ids=}"
        )
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")

        sessions = []
        for account_id in self.target_accounts:
            account_details: CoveSessionInformation = CoveSessionInformation(
                Id=account_id,
                RoleName=self.role_to_assume,
                RoleSessionName=self.role_session_name,
                Policy=self.policy,
                PolicyArns=self.policy_arns,
                AssumeRoleSuccess=False,
                ExceptionDetails=None,
                Name=None,
                Arn=None,
                Email=None,
                Status=None,
                Result=None,
            )
            sessions.append(account_details)

        return sessions

    def _get_boto3_client(
        self,
        clientname: Union[Literal["organizations"], Literal["sts"]],
        assuming_session: Optional[Session],
    ) -> Any:
        if assuming_session:
            logger.info(f"Using provided Boto3 session {assuming_session}")
            return assuming_session.client(
                service_name=clientname, config=Config(max_pool_connections=20)
            )
        logger.info("No Boto3 session argument: using credential chain")
        return boto3.client(
            service_name=clientname, config=Config(max_pool_connections=20)
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

    def _resolve_target_accounts(self, target_ids: Optional[List[str]]) -> Set[str]:
        if self.provided_ignore_ids:
            validated_ignore_ids = self._format_ignore_ids()
        else:
            validated_ignore_ids = set()

        if target_ids is None:
            # No target_ids passed
            target_accounts = self._gather_org_assume_targets()
        else:
            target_accounts, target_ous = self._validate_target_accounts(target_ids)
            target_accounts_from_ous = self._get_all_accounts_by_organization_units(
                target_ous
            )
            target_accounts.extend(target_accounts_from_ous)

            target_accounts = set(target_accounts)

        return target_accounts - validated_ignore_ids

    def _validate_target_accounts(
        self, target_ids: Optional[List[str]]
    ) -> Tuple[List[str], List[str]]:

        target_accounts = list()
        target_ous = []

        for target_id in target_ids:
            if not isinstance(target_id, str):
                raise TypeError("All target_id list entries must be strings")
            if re.match(r"^\d{12}$", target_id):
                target_accounts.append(target_id)
                continue
            if re.match(r"^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$", target_id):
                target_ous.append(target_id)
                continue
            raise ValueError(
                f"target_ids entry is neither an aws account nor an ou: {target_id}"
            )

        return target_accounts, target_ous

    def _get_all_accounts_by_organization_units(
        self, target_ous: Optional[List[str]]
    ) -> List[str]:

        account_list = list()

        for parent_ou in target_ous:

            current_ou_list = []
            self._get_all_child_ous(parent_ou, current_ou_list)

            # for complete list add parent ou as well to list of child ous
            current_ou_list.append(parent_ou)

            account_list.extend(
                self._get_accounts_by_organization_units(current_ou_list)
            )

        return account_list

    def _get_all_child_ous(
        self, parent_ou: str, ou_list: Optional[List[str]] = None
    ) -> List[str]:

        if ou_list == None:
            ou_list = []

        extraArgs = {"ChildType": "ORGANIZATIONAL_UNIT", "ParentId": parent_ou}

        paginator = self.org_client.get_paginator("list_children")
        list_ou_children = paginator.paginate(
            ChildType="ORGANIZATIONAL_UNIT", ParentId=parent_ou
        ).build_full_result()

        ous_batch = [child["Id"] for child in list_ou_children["Children"]]
            ous_batch = [child["Id"] for child in page["Children"]]
            ou_list.extend(ous_batch)
            for ou in ous_batch:
                self._get_all_child_ous(ou, ou_list)

        return ou_list

    def _get_accounts_by_organization_units(
        self, organization_units: Optional[List[str]]
    ) -> List[str]:

        account_list = list()

        for ou in organization_units:

            extraArgs = {"ChildType": "ACCOUNT", "ParentId": ou}

            paginator = self.org_client.get_paginator("list_children")
            page_iterator = paginator.paginate(**extraArgs)

            for page in page_iterator:
                accounts_batch = [x["Id"] for x in page["Children"]]
                account_list.extend(accounts_batch)

        return account_list

    def _format_ignore_ids(self) -> Set[str]:
        if not isinstance(self.provided_ignore_ids, list):
            raise TypeError("ignore_ids must be a list of account IDs")
        for account_id in self.provided_ignore_ids:
            if len(account_id) != 12:
                raise TypeError("All ignore_id in list must be 12 character strings")
            if not isinstance(account_id, str):
                raise TypeError("All ignore_id list entries must be strings")
        return set(self.provided_ignore_ids)

    def _get_active_org_accounts(self) -> Set[str]:
        all_org_accounts = (
            self.org_client.get_paginator("list_accounts")
            .paginate()
            .build_full_result()["Accounts"]
        )
        return {acc["Id"] for acc in all_org_accounts if acc["Status"] == "ACTIVE"}

    def _build_account_ignore_list(self) -> Set[str]:
        accounts_to_ignore: Set[str] = {
            self.sts_client.get_caller_identity()["Account"]
        }
        if self.provided_ignore_ids:
            accounts_to_ignore.update(self.provided_ignore_ids)

        logger.info(f"{accounts_to_ignore=}")
        return accounts_to_ignore

    def _gather_org_assume_targets(self) -> Set[str]:
        accounts_to_ignore = self._build_account_ignore_list()
        active_accounts = self._get_active_org_accounts()
        target_accounts = active_accounts - accounts_to_ignore
        return target_accounts

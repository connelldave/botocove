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
    cast,
)

import boto3
from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import ClientError
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_organizations.type_defs import (
    AccountTypeDef,
    ListChildrenResponseTypeDef,
)
from mypy_boto3_sts.client import STSClient
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef

from botocove.cove_types import CoveSessionInformation

logger = logging.getLogger(__name__)


DEFAULT_ROLENAME = "OrganizationAccountAccessRole"


class CoveHostAccount(object):
    target_regions: Sequence[Optional[str]]
    account_data: Optional[Dict[str, AccountTypeDef]] = None

    def __init__(
        self,
        target_ids: Optional[List[str]],
        ignore_ids: Optional[List[str]],
        rolename: Optional[str],
        role_session_name: Optional[str],
        policy: Optional[str],
        policy_arns: Optional[List[PolicyDescriptorTypeTypeDef]],
        assuming_session: Optional[Session],
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

        try:
            self.organization_account_ids: Set[str] = self._get_active_org_accounts()
        except ClientError as e:
            logger.info(
                "Cove does not have the ability to call ListAccounts - "
                "https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html"  # noqa: E501
            )
            logger.info(
                "Cove will only run with declared target IDs and will not enrich data "
                "in session information."
            )
            logger.debug(f"Exception raised was {e}")

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

    def get_cove_sessions(self) -> List[CoveSessionInformation]:
        logger.info(f"Getting session information for {self.target_accounts=}")
        logger.info(f"Role: {self.role_to_assume=} {self.role_session_name=}")
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")
        return list(self._generate_account_sessions())

    def _generate_account_sessions(self) -> Iterable[CoveSessionInformation]:
        for region in self.target_regions:
            for account_id in self.target_accounts:
                if self.account_data is not None:
                    yield CoveSessionInformation(
                        Id=account_id,
                        RoleName=self.role_to_assume,
                        RoleSessionName=self.role_session_name,
                        Policy=self.policy,
                        PolicyArns=self.policy_arns,
                        AssumeRoleSuccess=False,
                        Region=region,
                        ExceptionDetails=None,
                        Name=self.account_data[account_id]["Name"],
                        Arn=self.account_data[account_id]["Arn"],
                        Email=self.account_data[account_id]["Email"],
                        Status=self.account_data[account_id]["Status"],
                        Result=None,
                    )
                else:
                    yield CoveSessionInformation(
                        Id=account_id,
                        RoleName=self.role_to_assume,
                        RoleSessionName=self.role_session_name,
                        Policy=self.policy,
                        PolicyArns=self.policy_arns,
                        AssumeRoleSuccess=False,
                        Region=region,
                        ExceptionDetails=None,
                        Name=None,
                        Arn=None,
                        Email=None,
                        Status=None,
                        Result=None,
                    )

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

    def _resolve_target_accounts(self, target_ids: Optional[List[str]]) -> Set[str]:
        accounts_to_ignore = self._gather_ignored_accounts()
        logger.info(f"Ignoring account IDs: {accounts_to_ignore=}")
        accounts_to_target = self._gather_target_accounts(target_ids)
        final_accounts: Set = accounts_to_target - accounts_to_ignore
        if len(final_accounts) < 1:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )
        return final_accounts

    def _gather_ignored_accounts(self) -> Set[str]:
        ignored_accounts = {self.host_account_id}

        if self.provided_ignore_ids:
            accs, ous = self._get_validated_ids(self.provided_ignore_ids)
            ignored_accounts.update(accs)
            if ous:
                accs_from_ous = self._get_all_accounts_by_organization_units(ous)
                ignored_accounts.update(accs_from_ous)

        return ignored_accounts

    def _gather_target_accounts(self, targets: Optional[List[str]]) -> Set[str]:
        if targets:
            accs, ous = self._get_validated_ids(targets)
            if ous:
                accs_from_ous = self._get_all_accounts_by_organization_units(ous)
                accs.extend(accs_from_ous)
            return set(accs)
        else:
            # No target_ids passed, getting all accounts in org
            return self.organization_account_ids

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
    ) -> List[str]:

        account_list: List[str] = []

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
        child_ous_list = [ou["Id"] for ou in child_ous["Children"]]
        ou_list.extend(child_ous_list)

        for ou in child_ous_list:
            self._get_all_child_ous(ou, ou_list)

    def _get_accounts_by_organization_units(
        self, organization_units: List[str]
    ) -> List[str]:

        account_list: List[str] = []

        for ou in organization_units:
            ou_children = self._get_child_accounts(ou)
            account_list.extend(acc["Id"] for acc in ou_children["Children"])

        return account_list

    def _get_active_org_accounts(self) -> Set[str]:
        """
        Captures all account metadata into self.account_data for future lookup
        and returns a set of account IDs in the AWS organization.
        """
        pages = self.org_client.get_paginator("list_accounts").paginate()
        self.account_data: Dict[str, AccountTypeDef] = {
            account["Id"]: account
            for page in pages
            for account in page["Accounts"]
            if account["Status"] == "ACTIVE"
        }

        return set(self.account_data.keys())

    @lru_cache()
    def _get_child_ous(self, parent_ou: str) -> ListChildrenResponseTypeDef:
        try:
            return cast(
                ListChildrenResponseTypeDef,
                self.org_client.get_paginator("list_children")
                .paginate(ChildType="ORGANIZATIONAL_UNIT", ParentId=parent_ou)
                .build_full_result(),
            )
        except ClientError:
            logger.error(
                "Cove can only look up target accounts by OU when running from the "
                "organization's management account or by a member account that is a "
                "delegated administrator for an AWS service: "
                "https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListChildren.html"  # noqa: E501
            )
            raise

    @lru_cache()
    def _get_child_accounts(self, parent_ou: str) -> ListChildrenResponseTypeDef:
        return cast(
            ListChildrenResponseTypeDef,
            self.org_client.get_paginator("list_children")
            .paginate(ChildType="ACCOUNT", ParentId=parent_ou)
            .build_full_result(),
        )

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
from botocore.exceptions import ClientError
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_organizations.type_defs import AccountTypeDef
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
        external_id: Optional[str],
        assuming_session: Optional[Session],
        thread_workers: int,
        regions: Optional[List[str]],
        partition: Optional[str],
    ) -> None:

        self.thread_workers = thread_workers

        self.sts_client = self._get_boto3_sts_client(assuming_session)
        self.org_client = self._get_boto3_org_client(assuming_session)

        caller_id = self.sts_client.get_caller_identity()
        self.host_account_id = caller_id["Account"]
        self.host_account_partition = caller_id["Arn"].split(":")[1]

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

        self.partition = partition or self.host_account_partition
        self.role_to_assume = rolename or DEFAULT_ROLENAME
        self.role_session_name = role_session_name or self.role_to_assume
        self.policy = policy
        self.policy_arns = policy_arns
        self.external_id = external_id

    def get_cove_sessions(self) -> List[CoveSessionInformation]:
        logger.info(f"Getting session information for {self.target_accounts=}")
        logger.info(f"AWS Partition: {self.partition=}")
        logger.info(f"Role: {self.role_to_assume=} {self.role_session_name=}")
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")
        return list(self._generate_account_sessions())

    def _generate_account_sessions(self) -> Iterable[CoveSessionInformation]:
        for region in self.target_regions:
            for account_id in self.target_accounts:
                if self.account_data is not None:

                    # If running with target accounts, but with organization data
                    # available, i.e., running from org master but not targeting
                    # whole org.
                    if account_id not in self.account_data:
                        raise ValueError(
                            f"Account {account_id} is not ACTIVE in the organization."
                        )

                    yield CoveSessionInformation(
                        Id=account_id,
                        RoleName=self.role_to_assume,
                        RoleSessionName=self.role_session_name,
                        Policy=self.policy,
                        PolicyArns=self.policy_arns,
                        ExternalId=self.external_id,
                        AssumeRoleSuccess=False,
                        Region=region,
                        Partition=self.partition,
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
                        ExternalId=self.external_id,
                        AssumeRoleSuccess=False,
                        Region=region,
                        Partition=self.partition,
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
        final_accounts: Set[str] = accounts_to_target - accounts_to_ignore
        if len(final_accounts) < 1:
            raise ValueError(
                "There are no eligible account ids to run decorated func against"
            )
        return final_accounts

    def _gather_ignored_accounts(self) -> Set[str]:
        ignored_accounts = {self.host_account_id}
        if self.provided_ignore_ids:
            ignored_accounts |= self._gather_accounts(self.provided_ignore_ids)
        return ignored_accounts

    def _gather_target_accounts(self, targets: Optional[List[str]]) -> Set[str]:
        if targets:
            return self._gather_accounts(targets)
        return self.organization_account_ids

    def _gather_accounts(self, resources: List[str]) -> Set[str]:
        parsed_accounts, parsed_ous = self._get_validated_ids(resources)

        if not parsed_ous:
            return parsed_accounts

        traversed_accounts = self._list_accounts_for_ancestors(parsed_ous)
        return parsed_accounts | traversed_accounts

    def _get_validated_ids(self, ids: List[str]) -> Tuple[Set[str], Set[str]]:

        accounts: Set[str] = set()
        ous: Set[str] = set()

        for current_id in ids:
            if not isinstance(current_id, str):
                raise TypeError(
                    f"{current_id} is an incorrect type: all account and ou id's must be strings not {type(current_id)}"  # noqa E501
                )
            if re.match(r"^\d{12}$", current_id):
                accounts.add(current_id)
                continue
            if re.match(r"^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$", current_id):
                ous.add(current_id)
                continue
            raise ValueError(
                f"provided id is neither an aws account nor an ou: {current_id}"
            )

        return accounts, ous

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

    def _list_accounts_for_ancestors(self, ancestor_ous: Set[str]) -> Set[str]:
        """Lists all descendant accounts for the list of ancestor OUs."""
        return {
            account
            for ou in ancestor_ous
            for account in self._list_accounts_for_ancestor(ou)
        }

    def _list_accounts_for_ancestor(self, ancestor_ou: str) -> Set[str]:
        """Lists all descendant accounts for the ancestor OU."""
        ous_in_tree = self._list_ous_for_ancestor(ancestor_ou)
        return {
            account for ou in ous_in_tree for account in self._get_child_accounts(ou)
        }

    def _list_ous_for_ancestor(self, ancestor_ou: str) -> Set[str]:
        """Lists all descendant OUs for the ancestor OUs. Includes self."""
        ous_in_tree: Set[str] = {ancestor_ou}
        child_ous = self._get_child_ous(ancestor_ou)
        if not child_ous:
            return ous_in_tree
        for ou in child_ous:
            ous_in_tree |= self._list_ous_for_ancestor(ou)
        return ous_in_tree

    @lru_cache()
    def _get_child_ous(self, parent_ou: str) -> Set[str]:
        """List the child organizational units (OUs) of the parent OU. Just the ID
        is needed to traverse the organization tree."""
        try:
            pages = self.org_client.get_paginator(
                "list_organizational_units_for_parent"
            ).paginate(ParentId=parent_ou)
            return {ou["Id"] for page in pages for ou in page["OrganizationalUnits"]}
        except ClientError:
            logger.error(
                "Cove can only look up target accounts by OU when running from the "
                "organization's management account or by a member account that is a "
                "delegated administrator for an AWS service: "
                "https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListChildren.html"  # noqa: E501
            )
            raise

    @lru_cache()
    def _get_child_accounts(self, parent_ou: str) -> Set[str]:
        """List the child accounts of the parent organizational unit (OU). Just the ID is
        needed to access the account. The metedata is enriched elsewhere."""
        pages = self.org_client.get_paginator("list_accounts_for_parent").paginate(
            ParentId=parent_ou
        )
        return {account["Id"] for page in pages for account in page["Accounts"]}

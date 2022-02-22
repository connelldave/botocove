import logging
from typing import Any, Iterable, List, Literal, Optional, Sequence, Set, Union

import boto3
from boto3.session import Session
from botocore.config import Config
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_sts.client import STSClient

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
        policy_arns: Optional[List[str]],
        assuming_session: Optional[Session],
        org_master: bool,
        thread_workers: int,
        regions: Optional[List[str]],
    ) -> None:

        self.thread_workers = thread_workers

        self.sts_client = self._get_boto3_sts_client(assuming_session)
        self.org_client = self._get_boto3_org_client(assuming_session)

        if regions is None:
            self.target_regions = [None]
        else:
            self.target_regions = regions

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

    def get_cove_sessions(self) -> List[CoveSessionInformation]:
        logger.info(f"Getting session information qfor {self.target_accounts=}")
        logger.info(f"Role: {self.role_to_assume=} {self.role_session_name=}")
        logger.info(f"Session policy: {self.policy_arns=} {self.policy=}")
        return list(self._generate_account_sessions())

    def _generate_account_sessions(self) -> Iterable[CoveSessionInformation]:
        for region in self.target_regions:
            for account_id in self.target_accounts:
                account_details: CoveSessionInformation = CoveSessionInformation(
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

    def _resolve_target_accounts(self, target_ids: Optional[List[str]]) -> Set[str]:
        # Ensure we never run botocove on the account it's being run from
        running_account_id = self.sts_client.get_caller_identity()["Account"]
        validated_ignore_ids = set(running_account_id)

        if self.provided_ignore_ids:
            validated_ignore_ids.update(self._format_ignore_ids())
        logger.info(f"Ignoring account IDs: {validated_ignore_ids=}")

        if target_ids is None:
            # No target_ids passed
            validated_ignore_ids.update()
            target_accounts = self._get_active_org_accounts()
        else:
            # Specific list of IDs passed
            target_accounts = set(target_ids)

        return target_accounts - validated_ignore_ids

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

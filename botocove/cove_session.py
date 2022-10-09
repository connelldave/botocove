import logging
from typing import Any

from boto3.session import Session
from botocore.exceptions import ClientError
from mypy_boto3_sts.client import STSClient

from botocove.cove_types import CoveSessionInformation

logger = logging.getLogger(__name__)


class CoveSession(Session):
    """Enriches a boto3 Session with account data from Master account if run from
    an organization master.
    Provides internal helper functions for managing concurrent boto3 calls
    """

    assume_role_success: bool = False
    session_information: CoveSessionInformation
    stored_exception: Exception

    def __init__(
        self,
        session_info: CoveSessionInformation,
        sts_client: STSClient,
    ) -> None:
        self.session_information = session_info
        self.sts_client = sts_client

    def __repr__(self) -> str:
        # Overwrite boto3's repr to avoid AttributeErrors
        return f"{self.__class__.__name__}(account_id={self.session_information['Id']})"

    def activate_cove_session(self) -> "CoveSession":
        role_arn = (
            f"arn:aws:iam::{self.session_information['Id']}:role/"
            f"{self.session_information['RoleName']}"
        )

        try:
            logger.debug(f"Attempting to assume {role_arn}")

            # This calling style avoids a ParamValidationError from botocore.
            # Passing None is not allowed for the optional parameters.
            assume_role_args = {
                k: v
                for k, v in [
                    ("RoleArn", role_arn),
                    ("RoleSessionName", self.session_information["RoleSessionName"]),
                    ("Policy", self.session_information["Policy"]),
                    ("PolicyArns", self.session_information["PolicyArns"]),
                ]
                if v is not None
            }
            creds = self.sts_client.assume_role(**assume_role_args)["Credentials"]  # type: ignore[arg-type] # noqa E501

            init_session_args = {
                k: v
                for k, v in [
                    ("aws_access_key_id", creds["AccessKeyId"]),
                    ("aws_secret_access_key", creds["SecretAccessKey"]),
                    ("aws_session_token", creds["SessionToken"]),
                    ("region_name", self.session_information["Region"]),
                ]
                if v is not None
            }

            self.initialize_boto_session(**init_session_args)
            self.session_information["AssumeRoleSuccess"] = True
        except ClientError:
            logger.error(
                f"Failed to initalize cove session for "
                f"account {self.session_information['Id']}"
            )
            raise

        return self

    def initialize_boto_session(self, *args: Any, **kwargs: Any) -> None:
        # Inherit from and initialize standard boto3 Session object
        super().__init__(*args, **kwargs)

    def format_cove_result(self, result: Any) -> CoveSessionInformation:
        self.session_information["Result"] = result
        return self.session_information

    def format_cove_error(self, err: Exception) -> CoveSessionInformation:
        self.session_information["ExceptionDetails"] = err
        return self.session_information

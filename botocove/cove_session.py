from typing import Any

from boto3.session import Session

from botocove.cove_types import CoveSessionInformation, R


class CoveSession(Session):
    """Enriches a boto3 Session with account data from Master account if run from
    an organization master.
    Provides internal helper functions for managing concurrent boto3 calls
    """

    assume_role_success: bool = False
    session_information: CoveSessionInformation
    stored_exception: Exception

    def __init__(self, session_info: CoveSessionInformation) -> None:
        self.session_information = session_info

    def __repr__(self) -> str:
        # Overwrite boto3's repr to avoid AttributeErrors
        return f"{self.__class__.__name__}(account_id={self.session_information.Id})"

    def initialize_boto_session(self, *args: Any, **kwargs: Any) -> None:
        # Inherit from and initialize standard boto3 Session object
        super().__init__(*args, **kwargs)
        self.assume_role_success = True
        self.session_information.AssumeRoleSuccess = self.assume_role_success

    def store_exception(self, err: Exception) -> None:
        self.stored_exception = err

    def format_cove_result(self, result: R) -> CoveSessionInformation:
        self.session_information.Result = result
        return self.session_information

    def format_cove_error(self) -> CoveSessionInformation:
        self.session_information.ExceptionDetails = self.stored_exception
        self.session_information.AssumeRoleSuccess = self.assume_role_success
        return self.session_information

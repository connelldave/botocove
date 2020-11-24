from typing import Any, Dict, List

from boto3.session import Session
from botocore.exceptions import ClientError


class CoveSession(Session):
    """Enriches a boto3 Session with account data from Master account if run from
    an organization master.
    Provides internal helper functions for managing concurrent boto3 calls
    """

    assume_role_success: bool = False
    session_information: Dict[str, Any] = {}
    stored_exceptions: List[Exception] = []

    def __init__(self, account_details: Dict[str, str]) -> None:
        ignore_fields = ["Arn", "JoinedMethod", "JoinedTimestamp"]
        for key in ignore_fields:
            account_details.pop(key, "Key not found")
        self.session_information = account_details

    def __repr__(self) -> str:
        # Overwrite boto3's repr to avoid AttributeErrors
        return f"{self.__class__.__name__}(account_id={self.session_information['Id']})"

    def initialize_boto_session(self, *args: Any, **kwargs: Any) -> None:
        # Inherit from and initialize standard boto3 Session object
        super().__init__(*args, **kwargs)
        self.assume_role_success = True
        self.session_information["AssumeRoleSuccess"] = self.assume_role_success

    def store_exception(self, exception: ClientError) -> None:
        if self.stored_exceptions:
            self.stored_exceptions.append(exception)
        else:
            self.stored_exceptions = [exception]

    def format_cove_result(self, result: Any) -> Dict[str, Any]:
        self.session_information["Result"] = result
        return self.session_information

    def format_cove_error(self) -> Dict[str, Any]:
        self.session_information["ExceptionDetails"] = self.stored_exceptions
        self.session_information["AssumeRoleSuccess"] = self.assume_role_success
        return self.session_information

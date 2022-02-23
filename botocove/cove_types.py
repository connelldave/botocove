from typing import Any, Dict, List, Optional, TypedDict

from mypy_boto3_organizations.literals import AccountStatusType


class CoveSessionInformation(TypedDict):
    Id: str
    RoleName: str
    AssumeRoleSuccess: bool
    Arn: Optional[str]
    Email: Optional[str]
    Name: Optional[str]
    Status: Optional[AccountStatusType]
    RoleSessionName: Optional[str]
    Policy: Optional[str]
    PolicyArns: Optional[List[str]]
    Result: Any
    ExceptionDetails: Optional[Exception]
    Region: Optional[str]


CoveResults = List[CoveSessionInformation]


class CoveFunctionOutput(TypedDict):
    Results: CoveResults
    Exceptions: CoveResults


class CoveOutput(TypedDict):
    Results: List[Dict[str, Any]]
    Exceptions: List[Dict[str, Any]]
    FailedAssumeRole: List[Dict[str, Any]]

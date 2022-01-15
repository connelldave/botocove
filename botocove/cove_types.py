from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypedDict, TypeVar

from mypy_boto3_organizations.literals import AccountStatusType

R = TypeVar("R")


@dataclass
class CoveSessionInformation(Generic[R]):
    Id: str
    Arn: Optional[str] = None
    Email: Optional[str] = None
    Name: Optional[str] = None
    Status: Optional[AccountStatusType] = None
    AssumeRoleSuccess: Optional[bool] = None
    RoleSessionName: Optional[str] = None
    Policy: Optional[str] = None
    PolicyArns: Optional[List[str]] = None
    Result: Optional[R] = None
    ExceptionDetails: Optional[Exception] = None


CoveResults = List[CoveSessionInformation]


class CoveFunctionOutput(TypedDict):
    Results: CoveResults
    Exceptions: CoveResults


class CoveOutput(TypedDict):
    Results: List[Dict[str, Any]]
    Exceptions: List[Dict[str, Any]]
    FailedAssumeRole: List[Dict[str, Any]]

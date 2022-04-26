from typing import Any, Dict, List, Optional, TypedDict

from mypy_boto3_organizations.literals import AccountStatusType
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef


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
    PolicyArns: Optional[List[PolicyDescriptorTypeTypeDef]]
    Result: Any
    ExceptionDetails: Optional[Exception]
    Region: Optional[str]


class CoveFunctionOutput(TypedDict):
    Results: List[CoveSessionInformation]
    Exceptions: List[CoveSessionInformation]


class CoveOutput(TypedDict):
    Results: List[Dict[str, Any]]
    Exceptions: List[Dict[str, Any]]
    FailedAssumeRole: List[Dict[str, Any]]

import functools
import logging
from typing import Any, Callable, Dict, List, Optional
from warnings import warn

from boto3.session import Session
from mypy_boto3_sts.type_defs import PolicyDescriptorTypeTypeDef

from botocove.cove_host_account import CoveHostAccount
from botocove.cove_runner import CoveRunner
from botocove.cove_types import CoveOutput

logger = logging.getLogger(__name__)


def cove(
    _func: Optional[Callable[..., Any]] = None,
    *,
    target_ids: Optional[List[str]] = None,
    ignore_ids: Optional[List[str]] = None,
    rolename: Optional[str] = None,
    role_session_name: Optional[str] = None,
    policy: Optional[str] = None,
    policy_arns: Optional[List[PolicyDescriptorTypeTypeDef]] = None,
    assuming_session: Optional[Session] = None,
    raise_exception: bool = False,
    thread_workers: int = 20,
    regions: Optional[List[str]] = None,
    **cove_kwargs: Any,
) -> Callable:
    def decorator(func: Callable[..., Any]) -> Callable[..., CoveOutput]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> CoveOutput:

            _check_deprecation(cove_kwargs)

            _typecheck_regions(regions)
            _typecheck_id_list(target_ids)
            _typecheck_id_list(ignore_ids)

            host_account = CoveHostAccount(
                target_ids=target_ids,
                ignore_ids=ignore_ids,
                rolename=rolename,
                role_session_name=role_session_name,
                policy=policy,
                policy_arns=policy_arns,
                assuming_session=assuming_session,
                thread_workers=thread_workers,
                regions=regions,
            )

            runner = CoveRunner(
                host_account=host_account,
                func=func,
                raise_exception=raise_exception,
                func_args=args,
                func_kwargs=kwargs,
                thread_workers=thread_workers,
            )

            output = runner.run_cove_function()

            # Rewrite dataclasses into untyped dicts to retain current functionality
            return CoveOutput(
                Results=[
                    {k: v for k, v in r.items() if v is not None}
                    for r in output["Results"]
                ],
                Exceptions=[
                    {k: v for k, v in e.items() if v is not None}
                    for e in output["Exceptions"]
                    if e["AssumeRoleSuccess"] is True
                ],
                FailedAssumeRole=[
                    {k: v for k, v in f.items() if v is not None}
                    for f in output["Exceptions"]
                    if f["AssumeRoleSuccess"] is False
                ],
            )

        return wrapper

    # Handle both bare decorator and with argument
    if _func is None:
        return decorator
    else:
        return decorator(_func)


def _typecheck_regions(list_of_regions: Optional[List[str]]) -> None:
    if list_of_regions is None:
        return
    if isinstance(list_of_regions, str):
        raise TypeError(
            f"regions must be a list of str. Got str {repr(list_of_regions)}."
        )


def _check_deprecation(kwargs: Dict[str, Any]) -> None:
    if "org_master" in kwargs:
        warn(
            "org_master is a deprecated kwarg since Cove 1.6.2 and has no effect",
            DeprecationWarning,
            stacklevel=2,
        )
    _raise_type_error_for_any_kwarg_except_org_master(kwargs)
    return None


def _raise_type_error_for_any_kwarg_except_org_master(kwargs: Dict[str, Any]) -> None:
    for key in kwargs:
        if key != "org_master":
            raise TypeError(f"Cove() got an unexpected keyword argument '{key}'")
    return None


def _typecheck_id_list(list_of_ids: Optional[List[str]]) -> None:
    if list_of_ids is None:
        return
    for _id in list_of_ids:
        _typecheck_id(_id)


def _typecheck_id(_id: str) -> None:
    if isinstance(_id, str):
        return
    raise TypeError(
        f"{_id} is an incorrect type: all account and ou id's must be strings "
        f"not {type(_id)}"
    )

import functools
import logging
from typing import Any, Callable, List, Optional

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
    org_master: bool = True,
    thread_workers: int = 20,
    regions: Optional[List[str]] = None,
) -> Callable:
    def decorator(func: Callable[..., Any]) -> Callable[..., CoveOutput]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> CoveOutput:

            _typecheck_regions(regions)

            host_account = CoveHostAccount(
                target_ids=target_ids,
                ignore_ids=ignore_ids,
                rolename=rolename,
                role_session_name=role_session_name,
                policy=policy,
                policy_arns=policy_arns,
                org_master=org_master,
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

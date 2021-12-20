import functools
import logging
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Iterable

from boto3.session import Session

from botocove.cove_runner import CoveRunner
from botocove.cove_sessions import CoveSessions
from botocove.cove_types import CoveOutput, CoveSessionInformation, R

logger = logging.getLogger(__name__)


def dataclass_converter(d: CoveSessionInformation) -> Dict[str, Any]:
    """Unpack dataclass into dict and remove None values"""
    return {k: v for k, v in asdict(d).items() if v}


def cove(
    _func: Optional[Callable[..., R]] = None,
    *,
    target_ids: Optional[List[str]] = None,
    ignore_ids: Optional[List[str]] = None,
    rolename: Optional[str] = None,
    role_session_name: Optional[str] = None,
    assuming_session: Optional[Session] = None,
    raise_exception: bool = False,
    org_master: bool = True,
) -> Callable:
    def decorator(func: Callable[..., R]) -> Callable[..., Iterable[Dict]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Iterable[Dict]:
            valid_sessions, invalid_sessions = CoveSessions(
                target_ids=target_ids,
                ignore_ids=ignore_ids,
                rolename=rolename,
                role_session_name=role_session_name,
                org_master=org_master,
                assuming_session=assuming_session,
            ).get_cove_sessions()

            runner = CoveRunner(
                valid_sessions=valid_sessions,
                func=func,
                raise_exception=raise_exception,
                func_args=args,
                func_kwargs=kwargs,
            )

            results, exceptions = runner.run_cove_function()

            return (
                map(dataclass_converter, invalid_sessions),
                map(dataclass_converter, results),
                map(dataclass_converter, exceptions)
            )

        return wrapper

    # Handle both bare decorator and with argument
    if _func is None:
        return decorator
    else:
        return decorator(_func)

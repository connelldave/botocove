import logging
from concurrent import futures
from typing import Any, Callable, List, Tuple

from tqdm import tqdm

from botocove.cove_session import CoveSession
from botocove.cove_types import (
    CoveFunctionOutput,
    CoveResults,
    CoveSessionInformation,
    R,
)

logger = logging.getLogger(__name__)


class CoveRunner(object):
    def __init__(
        self,
        sessions: List[CoveSession],
        func: Callable[..., R],
        raise_exception: bool,
        func_args: Any,
        func_kwargs: Any,
    ) -> None:
        self.sessions = sessions
        self.raise_exception = raise_exception
        self.cove_wrapped_func = func
        self.func_args = func_args
        self.func_kwargs = func_kwargs

    def run_cove_function(self) -> CoveFunctionOutput:
        # Run decorated func with all valid sessions
        results, exceptions = self._run_func_in_threads()
        return CoveFunctionOutput(
            Results=results,
            Exceptions=exceptions,
        )

    def cove_thread(
        self,
        account_session: CoveSession,
    ) -> CoveSessionInformation:
        try:
            cove_session = account_session.activate_cove_session()
            result = self.cove_wrapped_func(
                cove_session, *self.func_args, **self.func_kwargs
            )
            return cove_session.format_cove_result(result)
        except Exception as e:
            if self.raise_exception is True:
                account_session.store_exception(e)
                logger.exception(account_session.format_cove_error())
                raise
            else:
                account_session.store_exception(e)
                return account_session.format_cove_error()

    def _run_func_in_threads(
        self,
    ) -> Tuple[CoveResults, CoveResults]:
        with futures.ThreadPoolExecutor(max_workers=20) as executor:
            completed: CoveResults = list(
                tqdm(
                    executor.map(self.cove_thread, self.sessions),
                    total=len(self.sessions),
                    desc="Executing function",
                    colour="#ff69b4",  # hotpink
                )
            )

        successful_results = [
            result for result in completed if not result.ExceptionDetails
        ]
        exceptions = [result for result in completed if result.ExceptionDetails]
        return successful_results, exceptions

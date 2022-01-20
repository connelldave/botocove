import logging
from concurrent import futures
from typing import Any, Callable

from tqdm import tqdm

from botocove.cove_host_account import CoveHostAccount
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
        host_account: CoveHostAccount,
        func: Callable[..., R],
        raise_exception: bool,
        func_args: Any,
        func_kwargs: Any,
        thread_workers: int,
    ) -> None:

        self.host_account = host_account
        self.sessions = host_account.get_cove_session_info()

        self.cove_wrapped_func = func
        self.raise_exception = raise_exception
        self.func_args = func_args
        self.func_kwargs = func_kwargs

        self.thread_workers = thread_workers

    def run_cove_function(self) -> CoveFunctionOutput:
        # Run decorated func with all valid sessions
        with futures.ThreadPoolExecutor(max_workers=self.thread_workers) as executor:
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

        return CoveFunctionOutput(
            Results=successful_results,
            Exceptions=exceptions,
        )

    def cove_thread(
        self,
        account_session_info: CoveSessionInformation,
    ) -> CoveSessionInformation:
        cove_session = CoveSession(
            account_session_info,
            sts_client=self.host_account.sts_client,
            org_client=self.host_account.org_client,
            org_master=self.host_account.org_master,
        )
        try:
            cove_session.activate_cove_session()

            result = self.cove_wrapped_func(
                cove_session, *self.func_args, **self.func_kwargs
            )

            return cove_session.format_cove_result(result)

        except Exception as e:
            if self.raise_exception is True:
                logger.exception(cove_session.format_cove_error(e))
                raise
            else:
                return cove_session.format_cove_error(e)

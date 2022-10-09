import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, List

from tqdm import tqdm

from botocove.cove_host_account import CoveHostAccount
from botocove.cove_session import CoveSession
from botocove.cove_types import CoveFunctionOutput, CoveSessionInformation

logger = logging.getLogger(__name__)


class CoveRunner(object):
    def __init__(
        self,
        host_account: CoveHostAccount,
        func: Callable[..., Any],
        raise_exception: bool,
        func_args: Any,
        func_kwargs: Any,
        thread_workers: int,
    ) -> None:

        self.host_account = host_account
        self.sessions = host_account.get_cove_sessions()

        self.cove_wrapped_func = func
        self.raise_exception = raise_exception
        self.func_args = func_args
        self.func_kwargs = func_kwargs

        self.thread_workers = thread_workers

    def run_cove_function(self) -> CoveFunctionOutput:

        # The "Submit and Use as Completed" pattern as described in
        # "ThreadPoolExecutor in Python: The Complete Guide".
        # https://superfastpython.com/threadpoolexecutor-in-python/#Submit_and_Use_as_Completed
        with ThreadPoolExecutor(max_workers=self.thread_workers) as executor:
            futures: List["Future[CoveSessionInformation]"] = [
                executor.submit(self.cove_thread, s) for s in self.sessions
            ]
            completed: List[CoveSessionInformation] = list(
                tqdm(
                    _iterate_results_in_order_of_completion(futures),
                    total=len(self.sessions),
                    desc="Executing function",
                    colour="#ff69b4",  # hotpink
                )
            )

        successful_results = [
            result for result in completed if not result["ExceptionDetails"]
        ]
        exceptions = [result for result in completed if result["ExceptionDetails"]]

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


def _iterate_results_in_order_of_completion(
    jobs: List["Future[CoveSessionInformation]"],
) -> Iterable[CoveSessionInformation]:
    for f in as_completed(jobs):
        yield f.result()

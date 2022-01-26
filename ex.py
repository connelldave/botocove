from typing import List, Optional, TypedDict

from boto3 import Session

from botocove import cove


class CoveConfig(TypedDict):
    target_ids: Optional[List[str]]
    ignore_ids: Optional[List[str]]
    rolename: Optional[str]
    role_session_name: Optional[str]
    policy: Optional[str]
    policy_arns: Optional[List[str]]
    assuming_session: Optional[Session]
    raise_exception: bool
    org_master: bool
    thread_workers: int


CONST_STR = "hello"

InstantiatedConfig = CoveConfig(target_ids=["blah"])


@cove(**InstantiatedConfig)
def my_decorator(func):
    def wrapper():
        print("Something is happening before the function is called.")
        func()
        print("Something is happening after the function is called.")

    return wrapper


@cove
def say_whee():
    print("Whee!")


def cove_func():
    print("hello")


@my_decorator
def cove_func2():
    print("hi")

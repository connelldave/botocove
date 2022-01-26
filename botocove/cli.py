import importlib
import inspect
from types import ModuleType
from typing import Callable, List, Tuple

import click

from botocove import cove


@click.group()
@click.option(
    "--target",
    envvar="COVE_PATH",
    default=".",
    metavar="PATH",
    help="Changes the target collection folder location.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enables verbose mode.")
@click.version_option("1.0")
@click.pass_context
def cli(ctx, target, verbose):
    """Botocove's command line runner will collect any file named "cove_*.py"
    and will run "cove_" prefixed and decorated functions, in a manner similar
    to Pytest. It will then gather and output results per account
    """


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("files", nargs=-1, type=click.Path())
def collect(files):
    """Prints all functions to be run by Botocove"""
    # TODO no args - default to pwd with no depth
    # TODO take a dir or file as arg
    # TODO give this a -recurse arg to optionally find all subdirs
    # TODO print the config of each func: significantly which
    #  acc it'll run in under what creds?
    if not files:
        print("get all the files in tree")
        # filter for cove_ files
        files = []

    get_all_cove_funcs(files)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("files", nargs=-1, type=click.Path())
def run(files):
    """Runs all functions in files provided"""
    # TODO --auto-approve flag
    auto_approve = False
    # TODO no args - default to pwd with no depth
    # TODO take a dir or file as arg
    # TODO give this a -recurse arg to optionally find all subdirs
    # TODO print the config of each func: significantly which acc it'll run in under what creds?
    if not files:
        print("get all the files in the runnign folder")
        # filter for cove_ files
        files = []

    decorated, undecorated = get_all_cove_funcs(files)

    if not auto_approve:
        confirm = input("Confirm running these functions with Botocove by typing 'yes'")
        if confirm.lower() != "yes":
            print("Run cancelled")
            exit(0)

    all_outputs = []
    for f in undecorated:
        output = cove(f)
        all_outputs.append(output)

    for f in decorated:
        output = f()
        all_outputs.append(output)

    print(all_outputs)


def get_all_cove_funcs(files) -> Tuple[List[Callable], List[Callable]]:
    mods = get_all_modules(files)
    decorated_funcs = []
    undecorated_funcs = []
    for mod in mods:
        decorated, undecorated = get_cove_funcs(mod)
        decorated_funcs.extend(decorated)
        undecorated_funcs.extend(undecorated)

    print(decorated_funcs)
    print(undecorated_funcs)
    return decorated_funcs, undecorated_funcs


def get_all_modules(files):
    # TODO might need
    imported_modules = []
    for filename in files:
        if filename.endswith(".py") and filename.startswith("cove_"):
            try:
                m = importlib.import_module(filename.rstrip(".py"))
                imported_modules.append(m)
            except ImportError:
                print(f"failed to import {filename}")
    return imported_modules


def get_cove_funcs(mod: ModuleType) -> Tuple[List[Callable], List[Callable]]:
    decorated_funcs = []
    undecorated_funcs = []
    for f_name in dir(mod):
        f = getattr(mod, f_name)
        if inspect.isfunction(f):
            if cove_wrapped(f) is True:
                print(f"{f_name} is a cove wrapped func")
                decorated_funcs.append(f)
            if f_name.startswith("cove_"):
                print(f"{f_name} is a cove func")
                undecorated_funcs.append(f)
    return decorated_funcs, undecorated_funcs


def cove_wrapped(func: Callable) -> bool:
    """Recurse through all function objects in closure to check if they're a
    botocove decorator"""
    funcs_in_closure = get_all_wrappers(func)

    for f in funcs_in_closure:
        if (
            "botocove/botocove/decorator.py" in f.__code__.co_filename
            and f.__code__.co_name == "cove_wrapper"
        ):
            return True
    return False


def get_all_wrappers(f: Callable) -> List[Callable]:
    if not f.__closure__:
        return [f]
    decorators = []
    for closure in f.__closure__:
        if inspect.isfunction(closure.cell_contents):
            decorators.extend(get_all_wrappers(closure.cell_contents))
    return [f] + decorators

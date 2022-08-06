# Good intro to depreaction here: https://dev.to/hckjck/python-deprecation-2mof
# Python documentation: https://docs.python.org/3/library/warnings.html#testing-warnings

import warnings

import pytest
from boto3.session import Session

from botocove import cove
from tests.moto_mock_org.moto_models import SmallOrg


def test_when_org_master_is_unset_then_do_not_warn(mock_small_org: SmallOrg) -> None:
    @cove()
    def do_nothing(session: Session) -> None:
        pass

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("error")
        do_nothing()


@pytest.mark.parametrize("org_master", [True, False])
def test_when_org_master_is_set_then_warn(
    org_master: bool, mock_small_org: SmallOrg
) -> None:
    @cove(org_master=org_master)
    def do_nothing(session: Session) -> None:
        pass

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("error")

        with pytest.raises(
            DeprecationWarning,
            match="Don't set org_master. cove behaves as if it were True",
        ):

            do_nothing()


def test_when_unexpected_kwarg_passed_then_raises_type_error(
    mock_small_org: SmallOrg,
) -> None:
    @cove(fake_arg="fake_value")
    def do_nothing(session: Session) -> None:
        pass

    with pytest.raises(
        TypeError, match=r"cove\(\) got an unexpected keyword argument 'fake_arg'"
    ):
        do_nothing()

from botocove import CoveSession, cove
from tests.moto_mock_org.moto_models import SmallOrg


def test_decorated_simple_func(mock_small_org: SmallOrg) -> None:
    @cove()
    def simple_func(session: CoveSession) -> str:
        return "hello"

    cove_output = simple_func()
    # Two simple_func calls == two mock AWS accounts
    assert len(cove_output["Results"]) == 4

from pprint import pprint

from boto3 import Session
from moto import mock_organizations, mock_sts

from botocove import cove


@mock_sts  # type: ignore[misc]
@mock_organizations  # type: ignore[misc]
def main() -> None:
    create_org(Session(), number_of_member_accounts=100)
    cove_output = init_client_and_return_ok()
    pprint(cove_output)


@cove()
def init_client_and_return_ok(session: Session) -> str:
    session.client("ec2")
    return "OK"


def create_org(session: Session, number_of_member_accounts: int) -> None:
    client = session.client("organizations")
    client.create_organization(FeatureSet="ALL")
    for index in range(number_of_member_accounts):
        account_name = f"account_{index}"
        email = f"account_{index}@example.com"
        client.create_account(AccountName=account_name, Email=email)


if __name__ == "__main__":
    main()

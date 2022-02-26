from typing import List

import boto3
from mypy_boto3_organizations import OrganizationsClient


class SmallOrg:
    def __init__(self, session: boto3.Session):
        mock_org_client = session.client("organizations")

        # create org
        self.master_acc_id = mock_org_client.create_organization(
            FeatureSet="CONSOLIDATED_BILLING"
        )["Organization"]["MasterAccountId"]
        # Create 3 deep org nest
        # root -> 1 -> 2 -> 3
        # root -> 4
        root_id = mock_org_client.list_roots()["Roots"][0]["Id"]

        self.new_org1 = mock_org_client.create_organizational_unit(
            ParentId=root_id,
            Name="ou-1",
        )["OrganizationalUnit"]["Id"]
        self.new_org2 = mock_org_client.create_organizational_unit(
            ParentId=self.new_org1,
            Name="ou-2",
        )["OrganizationalUnit"]["Id"]
        self.new_org3 = mock_org_client.create_organizational_unit(
            ParentId=self.new_org2,
            Name="ou-3",
        )["OrganizationalUnit"]["Id"]

        # Create a second fork from root
        self.new_org4 = mock_org_client.create_organizational_unit(
            ParentId=root_id,
            Name="ou-4",
        )["OrganizationalUnit"]["Id"]

        self.account_group_one = create_accounts_in_ou(
            mock_org_client, 0, 3, root_id, self.new_org3
        )
        self.account_group_two = create_accounts_in_ou(
            mock_org_client, 4, 5, root_id, self.new_org4
        )

        self.all_accounts = self.account_group_one + self.account_group_two


class LargeOrg:
    def __init__(self, session: boto3.Session):
        mock_org_client: OrganizationsClient = session.client("organizations")

        # create org
        # root - A -> B
        #         \-> C
        # root - D
        self.master_acc_id = mock_org_client.create_organization(
            FeatureSet="CONSOLIDATED_BILLING"
        )["Organization"]["MasterAccountId"]

        # Create 3 deep org nest
        root_id = mock_org_client.list_roots()["Roots"][0]["Id"]

        # Member of root
        self.ou_A = mock_org_client.create_organizational_unit(
            ParentId=root_id,
            Name="ou-a",
        )["OrganizationalUnit"]["Id"]
        # Members of A
        self.ou_B = mock_org_client.create_organizational_unit(
            ParentId=self.ou_A,
            Name="ou-b",
        )["OrganizationalUnit"]["Id"]
        self.ou_C = mock_org_client.create_organizational_unit(
            ParentId=self.ou_A,
            Name="ou-c",
        )["OrganizationalUnit"]["Id"]
        # Member of root
        self.ou_D = mock_org_client.create_organizational_unit(
            ParentId=root_id,
            Name="ou-d",
        )["OrganizationalUnit"]["Id"]

        self.account_group_one = create_accounts_in_ou(
            mock_org_client, 0, 500, root_id, self.ou_B
        )

        self.account_group_two = create_accounts_in_ou(
            mock_org_client, 500, 1000, root_id, self.ou_C
        )

        self.account_group_three = create_accounts_in_ou(
            mock_org_client, 1000, 1500, root_id, self.ou_D
        )

        self.all_accounts = (
            self.account_group_one + self.account_group_two + self.account_group_three
        )


def create_accounts_in_ou(
    client: OrganizationsClient, start: int, stop: int, root_id: str, target_ou: str
) -> List[str]:
    account_ids = []
    for i in range(start, stop):
        acc_id = client.create_account(
            Email=f"mock{i}@mock.com", AccountName=f"mock{i}"
        )["CreateAccountStatus"]["AccountId"]
        # Move account to bottom of OU tree
        client.move_account(
            AccountId=acc_id,
            SourceParentId=root_id,
            DestinationParentId=target_ou,
        )
        account_ids.append(acc_id)
    return account_ids

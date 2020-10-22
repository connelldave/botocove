import json
from typing import Dict, Any
from async_all import async_all
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


EXCLUDE_ACCS = []

TARGET_ACCS = []


def scrape_iam():
    data = get_iam_humans()
    for zone in data:
        if zone.get("console_users"):
            print(json.dumps(zone, indent=4), "\n")


def scrape_dns():
    data = get_dns_zones()
    for zone in data:
        print(json.dumps(zone, indent=4), "\n\n")


def test_assume_role():
    test_role_works()


def get_account_id_and_alias(session):
    acc_id = session.client("sts").get_caller_identity().get("Account")
    acc_alias_list = (
        session.client("iam").list_account_aliases().get("AccountAliases", [])
    )

    if acc_alias_list:
        acc_alias = acc_alias_list[0]
    else:
        acc_alias = "No account alias"

    return acc_id, acc_alias


@async_all(
    ignore_ids=EXCLUDE_ACCS,
    rolename="OrganizationAccountAccessRole",
)
def test_role_works(session):
    return


@async_all
def get_dns_zones(session):
    acc_id, acc_alias = get_account_id_and_alias(session)

    r53 = session.client("route53", region_name="eu-west-1")
    zones = r53.get_paginator("list_hosted_zones").paginate().build_full_result()

    all_zone_records: Dict[str, Any] = {}
    for zone in zones["HostedZones"]:
        all_zone_records[zone["Name"]] = []
        zone_records = (
            r53.get_paginator("list_resource_record_sets")
            .paginate(HostedZoneId=zone["Id"])
            .build_full_result()
        )
        for record in zone_records["ResourceRecordSets"]:
            all_zone_records[zone["Name"]].append(record)

    return {
        "account_id": acc_id,
        "account_alias": acc_alias,
        "zone_records": all_zone_records,
    }


@async_all(ignore_ids=EXCLUDE_ACCS)
def get_iam_humans(session):
    acc_id, acc_alias = get_account_id_and_alias(session)

    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()

    console_users = []
    for user in all_users["Users"]:
        try:
            iam.get_login_profile(UserName=user["UserName"])
            console_users.append(user["UserName"])
        except Exception:
            continue

    return {
        "account_id": acc_id,
        "account_alias": acc_alias,
        "console_users": console_users,
    }


if __name__ == "__main__":
    # scrape_iam()
    # scrape_dns()
    test_assume_role()

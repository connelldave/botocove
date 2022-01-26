def cove_get_iam_users(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_users").paginate().build_full_result()
    return all_users


def cove_get_iam_roles(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_roles").paginate().build_full_result()
    return all_users


def cove_get_iam_policies(session):
    iam = session.client("iam", region_name="eu-west-1")
    all_users = iam.get_paginator("list_policies").paginate().build_full_result()
    return all_users

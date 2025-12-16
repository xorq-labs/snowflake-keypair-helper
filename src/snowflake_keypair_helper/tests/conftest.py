import pytest

from snowflake_keypair_helper.constants import (
    gh_test_role,
    gh_user,
)
from snowflake_keypair_helper.utils.con_utils import (
    connect_env,
    execute_statements,
)


def get_have_role_access(user=gh_user, role=gh_test_role):
    con = connect_env(user=user)
    dcts = execute_statements(con, f"SHOW GRANTS OF ROLE {role}")
    return any(dct.get("grantee_name") == user for dct in dcts)


have_gh_test_role_access = get_have_role_access(user=gh_user, role=gh_test_role)


def pytest_runtest_setup(item):
    if any(mark.name == "needs_gh_test_role_access" for mark in item.iter_markers()):
        if not have_gh_test_role_access:
            pytest.skip("cannot run X without Y")

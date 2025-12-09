from snowflake_keypair_helper.constants import (
    default_warehouse,
    gh_test_role,
    gh_test_user,
    gh_user,
)


def create_user(con, user=gh_test_user, default_warehouse=default_warehouse):
    from snowflake_keypair_helper.utils.con_utils import execute_statements

    statement = f"""
    USE ROLE USERADMIN;
    CREATE USER IF NOT EXISTS {user} TYPE = SERVICE DEFAULT_WAREHOUSE = {default_warehouse};
    """
    return execute_statements(con, statement)


def create_and_grant_modify_auth_role(
    con, role=gh_test_role, on_user=gh_test_user, to_user=gh_user
):
    # https://docs.snowflake.com/en/user-guide/key-pair-auth#grant-the-privilege-to-assign-a-public-key-to-a-snowflake-user
    from snowflake_keypair_helper.utils.con_utils import execute_statements

    statement = f"""
    USE ROLE USERADMIN;
    CREATE ROLE IF NOT EXISTS {role};
    GRANT MODIFY PROGRAMMATIC AUTHENTICATION METHODS ON USER {on_user}
      TO ROLE {role};
    GRANT ROLE {role} TO USER {to_user};
    """
    return execute_statements(con, statement)

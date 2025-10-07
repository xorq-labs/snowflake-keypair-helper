import pytest
from cryptography.hazmat.primitives.serialization import (
    Encoding,
)
from snowflake.connector.errors import DatabaseError

from snowflake_keypair_helper.con_utils import (
    connect_env_keypair,
    connect_env_private_key,
    con_to_adbc_con,
    deassign_public_key,
    generate_and_assign_keypair,
)
from snowflake_keypair_helper.constants import (
    default_database,
    default_schema,
    gh_test_user,
    gh_user,
)
from snowflake_keypair_helper.crypto_utils import SnowflakeKeypair


@pytest.fixture
def con():
    con = connect_env_private_key()
    assert con.user == gh_user
    return con


@pytest.fixture
def keypair_from_env():
    keypair = SnowflakeKeypair.from_environment()
    return keypair


def test_defaults(con):
    actual = (con.database, con.schema)
    expected = (default_database, default_schema)
    assert actual == expected


def test_private_bytes_matches_environment(con, keypair_from_env):
    # check that con holds on to unencrypted DER
    assert (
        keypair_from_env.get_private_bytes(encoding=Encoding.DER, encrypted=False)
        == con._private_key
    )


def test_connect_adbc_from_con(con):
    adbc_con = con_to_adbc_con(con)
    expected = (con.database, con.schema)
    actual = (adbc_con.adbc_current_catalog, adbc_con.adbc_current_db_schema)
    assert actual == expected


@pytest.mark.xfail(reason="FIXME: install pyarrow")
def test_adbc_ingest():
    raise NotImplementedError


def test_connect_env_keypair(con, keypair_from_env):
    other = connect_env_keypair(keypair_from_env)
    assert con.user == other.user
    assert con._private_key == other._private_key


def test_connect_env_private_key_from_keypair_both_ways(keypair_from_env):
    # use encrypted key
    con0 = connect_env_private_key(
        private_key=keypair_from_env.private_str,
        private_key_pwd=keypair_from_env.private_key_pwd,
    )
    # use unencrypted key: if we pass unencrypted (bytes), we must override pwd
    con1 = connect_env_private_key(
        private_key=keypair_from_env.private_str_unencrypted, private_key_pwd=None
    )
    assert con0._private_key == con1._private_key


@pytest.mark.needs_gh_test_role_access
def test_assign_deassign_public_key(con):
    user = gh_test_user
    # this invokes assign_public_key
    path = generate_and_assign_keypair(con, user=user)
    new_keypair = SnowflakeKeypair.from_envrc(path)
    gh_test_user_con = connect_env_keypair(new_keypair, user=user)
    assert gh_test_user_con.user == user
    deassign_public_key(con, user)
    with pytest.raises(DatabaseError, match="Failed to connect.*JWT token is invalid"):
        connect_env_keypair(new_keypair, user=user)

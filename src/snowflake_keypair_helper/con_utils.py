import functools
import os
from enum import Enum

import adbc_driver_snowflake.dbapi as dbapi
from adbc_driver_snowflake import (
    DatabaseOptions,
)
from snowflake.connector import (
    connect,
)

from snowflake_keypair_helper.constants import (
    default_database,
    default_schema,
    snowflake_env_var_prefix,
)


class SnowflakeFields(Enum):
    private_key = ("private_key", "private_key_pwd")
    password = ("password",)
    password_mfa = ("password",)
    connection = ("account", "role", "warehouse", "user")


def make_env_name(name, prefix=snowflake_env_var_prefix):
    return f"{prefix}{name.upper()}"


def get_env_vars(*names, prefix=""):
    env_vars = {
        name: value
        for name, value in (
            (name, os.environ.get(make_env_name(name, prefix=prefix))) for name in names
        )
        if value is not None
    }
    return env_vars


(
    get_connection_defaults,
    get_credentials_defaults_private_key,
    get_credentials_defaults_password,
) = (
    functools.partial(get_env_vars, *fields.value, prefix=snowflake_env_var_prefix)
    for fields in (
        SnowflakeFields.connection,
        SnowflakeFields.private_key,
        SnowflakeFields.password,
    )
)


def connect_env_password(database=default_database, schema=default_schema, **overrides):
    kwargs = get_connection_defaults() | get_credentials_defaults_password() | overrides
    con = connect(database=database, schema=schema, **kwargs)
    return con


def connect_env_password_mfa(passcode, **overrides):
    return connect_env_password(passcode=passcode, **overrides)


def connect_env_private_key(
    database=default_database, schema=default_schema, **overrides
):
    from snowflake_keypair_helper.crypto_utils import (
        maybe_decrypt_private_key_snowflake,
    )

    kwargs = maybe_decrypt_private_key_snowflake(
        get_connection_defaults() | get_credentials_defaults_private_key() | overrides
    )
    con = connect(database=database, schema=schema, **kwargs)
    return con


def connect_env_envrc(
    envrc_path, database=default_database, schema=default_schema, **overrides
):
    from snowflake_keypair_helper.env_utils import with_envrc

    with with_envrc(envrc_path):
        con = connect_env_private_key(database=database, schema=schema, **overrides)
    return con


def connect_env_keypair(
    keypair, database=default_database, schema=default_schema, **overrides
):
    return connect_env_private_key(
        private_key=keypair.private_str,
        private_key_pwd=keypair.private_key_pwd,
        database=database,
        schema=schema,
        **overrides,
    )


def con_to_adbc_kwargs(
    con, database=default_database, schema=default_schema, **uri_overrides
):
    def make_uri(con, database, schema, **uri_overrides):
        params = (
            {attr: getattr(con, attr) for attr in ("user", "host", "warehouse", "role")}
            | {
                # ADBC connection always requires a password, even if using private key
                "password": con._password or "nopassword",
                "database": database,
                "schema": schema,
            }
            | uri_overrides
        )
        uri = f"{params['user']}:{params['password']}@{params['host']}/{params['database']}/{params['schema']}?warehouse={params['warehouse']}&role={params['role']}"
        return uri

    def make_db_kwargs(con):
        is_keypair_auth = (con._authenticator or "").upper() == "SNOWFLAKE_JWT"
        if is_keypair_auth:
            from snowflake_keypair_helper.crypto_utils import SnowflakeKeypair

            # we know the private key is unencrypted DER format
            keypair = SnowflakeKeypair.from_bytes_der(con._private_key)
            db_kwargs = {
                DatabaseOptions.AUTH_TYPE.value: "auth_jwt",
                DatabaseOptions.JWT_PRIVATE_KEY_VALUE.value: keypair.private_bytes,
                DatabaseOptions.JWT_PRIVATE_KEY_PASSWORD.value: keypair.private_key_pwd,
            }
        else:
            db_kwargs = {}
        return db_kwargs

    kwargs = {
        "uri": make_uri(con, database, schema, **uri_overrides),
        "db_kwargs": make_db_kwargs(con),
    }
    return kwargs


def con_to_adbc_con(con):
    adbc_kwargs = con_to_adbc_kwargs(con)
    return dbapi.connect(**adbc_kwargs)


def adbc_ingest(
    con, table_name, record_batch_reader, mode="create", temporary=False, **kwargs
):
    with con_to_adbc_con(con) as conn:
        with conn.cursor() as cur:
            cur.adbc_ingest(
                table_name,
                record_batch_reader,
                mode=mode,
                temporary=temporary,
                **kwargs,
            )
        # must commit!
        conn.commit()


def execute_statements(con, statements):
    def make_dcts(cursor):
        return tuple(
            dict(
                zip(
                    (el.name for el in cursor.description),
                    line,
                )
            )
            for line in cursor.fetchall()
        )

    cursors = con.execute_string(statements)
    fetched = tuple(dct for cursor in cursors for dct in make_dcts(cursor))
    return fetched


def assign_public_key(con, user, public_key_str, assert_value=True):
    from snowflake_keypair_helper.crypto_utils import remove_public_key_delimiters

    removed = remove_public_key_delimiters(public_key_str)
    statement = f"ALTER USER {user} SET RSA_PUBLIC_KEY='{removed}';"
    dcts = execute_statements(con, statement)
    if assert_value:
        assert dcts == ({"status": "Statement executed successfully."},), dcts
    return dcts


def deassign_public_key(con, user):
    statement = f"ALTER USER {user} UNSET RSA_PUBLIC_KEY;"
    return execute_statements(con, statement)

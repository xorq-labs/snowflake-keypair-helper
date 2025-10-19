import functools
import os
from enum import Enum

import toolz

from snowflake_keypair_helper.constants import (
    default_database,
    default_schema,
    snowflake_env_var_prefix,
)
from snowflake_keypair_helper.env_utils import (
    with_env_path,
)


try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum


class SnowflakeAuthenticator(StrEnum):
    # https://docs.snowflake.com/en/developer-guide/node-js/nodejs-driver-options#label-nodejs-auth-options
    password = "none"
    mfa = "username_password_mfa"
    keypair = "snowflake_jwt"
    sso = "externalbrowser"


class SnowflakeEnvFields(Enum):
    password = (
        "user",
        "password",
    )
    mfa = (
        "user",
        "password",
    )
    keypair = ("user", "private_key", "private_key_pwd")
    sso = ("user",)
    connection = ("account", "role", "warehouse")


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


def get_authenticator_credentials(
    authenticator=SnowflakeAuthenticator.keypair, prefix=snowflake_env_var_prefix
):
    match str(authenticator).lower():
        case (
            SnowflakeAuthenticator.password
            | SnowflakeAuthenticator.mfa
            | SnowflakeAuthenticator.keypair
            | SnowflakeAuthenticator.sso
        ):
            fields = SnowflakeEnvFields[authenticator.name]
            dct = get_env_vars(*fields.value, prefix=prefix)
            return dct
        case _:
            raise ValueError(f"Unknown authenticator: {authenticator}")


get_connection_defaults = toolz.curry(
    get_env_vars, *SnowflakeEnvFields.connection.value, prefix=snowflake_env_var_prefix
)


def maybe_process_keypair(kwargs):
    match kwargs:
        case {
            "authenticator": SnowflakeAuthenticator.keypair,
            "keypair": keypair,
            **rest,
        }:
            # prioritize keypair over ("private_key", "private_key_pwd")
            # if kwargs.get("private_key") or kwargs.get("private_key_pwd"):
            #     raise ValueError("cannot pass private_key or private_key_pwd when passing keypair")
            kwargs = rest | {
                "authenticator": SnowflakeAuthenticator.keypair,
                "private_key": keypair.private_str,
                "private_key_pwd": keypair.private_key_pwd,
            }
        case _:
            pass
    return kwargs


def connect_env(
    passcode=None,
    database=default_database,
    schema=default_schema,
    authenticator=SnowflakeAuthenticator.keypair,
    env_path=os.devnull,
    **overrides,
):
    from snowflake.connector import (
        connect,
    )
    from snowflake_keypair_helper.crypto_utils import (
        maybe_decrypt_private_key_snowflake,
    )

    with with_env_path(env_path):
        kwargs = (
            get_connection_defaults()
            | get_authenticator_credentials(authenticator)
            | {"passcode": passcode, "authenticator": authenticator}
            | overrides
        )
    kwargs = maybe_process_keypair(kwargs)
    kwargs = maybe_decrypt_private_key_snowflake(kwargs)
    con = connect(database=database, schema=schema, **kwargs)
    return con


connect_env_password = functools.partial(
    connect_env, authenticator=SnowflakeAuthenticator.password
)
connect_env_password_mfa = functools.partial(
    connect_env, authenticator=SnowflakeAuthenticator.mfa
)
connect_env_keypair = functools.partial(
    connect_env, authenticator=SnowflakeAuthenticator.keypair
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
            from adbc_driver_snowflake import (
                DatabaseOptions,
            )
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
    import adbc_driver_snowflake.dbapi as dbapi

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

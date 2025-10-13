from enum import Enum


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


class SnowflakeFields(StrEnum):
    account = "account"
    role = "role"
    warehouse = "warehouse"
    user = "user"
    password = "password"
    private_key = "private_key"
    private_key_pwd = "private_key_pwd"
    authenticator = "authenticator"
    passcode = "passcode"
    database = "database"
    schema = "schema"
    host = "host"


class SnowflakeEnvFields(Enum):
    password = (
        SnowflakeFields.user,
        SnowflakeFields.password,
    )
    mfa = (
        SnowflakeFields.user,
        SnowflakeFields.password,
    )
    keypair = (
        SnowflakeFields.user,
        SnowflakeFields.private_key,
        SnowflakeFields.private_key_pwd,
    )
    sso = (SnowflakeFields.user,)
    connection = (
        SnowflakeFields.account,
        SnowflakeFields.role,
        SnowflakeFields.warehouse,
    )

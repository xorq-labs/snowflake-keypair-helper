from cryptography.hazmat.primitives.serialization import (
    Encoding,
)

from snowflake_keypair_helper.enums import (
    SnowflakeFields,
)
from snowflake_keypair_helper.general_utils import (
    encode_utf8,
    make_private_key_pwd,
)
from snowflake_keypair_helper.snowflake_keypair import (
    SnowflakeKeypair,
)


def decrypt_private_bytes_snowflake(private_bytes: bytes, password_str: str):
    # encrypted PEM to unencrypted DER: for snowflake.connector.connect
    return SnowflakeKeypair.from_bytes_pem(
        private_bytes, password_str
    ).get_private_bytes(encoding=Encoding.DER, encrypted=False)


def encrypt_private_bytes_snowflake_adbc(private_bytes: bytes, password_str: str):
    # unencrypted DER to encrypted PEM: for adbc_driver_snowflake.dbapi.connect
    return (
        SnowflakeKeypair.from_bytes_der(private_bytes, None)
        .with_password(password_str)
        .private_bytes
    )


def maybe_decrypt_private_key_snowflake(kwargs: dict):
    # # SnowflakeConnection requires unencrypted DER format
    # ProgrammingError: 251008: Failed to decode private key: Incorrect padding
    # Please provide a valid unencrypted rsa private key in base64-encoded DER format as a str object
    match kwargs:
        case {
            SnowflakeFields.private_key: private_key,
            SnowflakeFields.private_key_pwd: private_key_pwd,
            **rest,
        }:
            assert isinstance(private_key, str)
            kwargs = rest | {
                SnowflakeFields.private_key: decrypt_private_bytes_snowflake(
                    encode_utf8(private_key), private_key_pwd
                )
            }
        case {SnowflakeFields.private_key: private_key, **rest}:
            assert isinstance(private_key, bytes)
            # ctor will fail if other than unencrypted DER format (bytes)
            SnowflakeKeypair.from_bytes_der(private_key)
        case _:
            raise ValueError(
                f"`{SnowflakeFields.private_key}` not found in kwargs: {tuple(kwargs)}"
            )
    return kwargs


def maybe_encrypt_private_key_snowflake_adbc(
    private_key: str, private_key_pwd: str, k: int = 20
):
    # adbc_driver_snowflake.dbapi.connect requires encrypted PEM format
    match (private_key, private_key_pwd):
        case [str(private_key_encrypted), str()]:
            pass
        case [str(), None]:
            private_key_pwd = make_private_key_pwd(k=k)
            private_key_encrypted = encrypt_private_bytes_snowflake_adbc(
                encode_utf8(private_key),
                private_key_pwd,
            )
        case _:
            raise ValueError(
                f"invalid types: {(type(private_key), type(private_key_pwd))}"
            )
    return (private_key_encrypted, private_key_pwd)


def generate_private_str(password=None):
    # # equivalent to https://docs.snowflake.com/en/user-guide/key-pair-auth#generate-the-private-keys
    # maybe_passout_arg = f"-passout 'pass:{password}'" if password else "-nocrypt"
    # f"openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out - {maybe_passout_arg}"
    return SnowflakeKeypair.generate(password=password).private_str

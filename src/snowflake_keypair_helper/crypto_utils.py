import os
import random
import string
from dataclasses import (
    dataclass,
    field,
    replace,
)
from pathlib import Path
from typing import Optional

import cryptography.hazmat.primitives.asymmetric.rsa as rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_der_private_key,
    load_pem_private_key,
)

from snowflake_keypair_helper.constants import (
    snowflake_env_var_prefix,
    default_env_path,
)
from snowflake_keypair_helper.dataclass_utils import (
    validate_dataclass_types,
)


def make_user_envrc_path(user):
    return Path(f"{user.upper()}.envrc.secrets.snowflake.keypair")


def make_private_key_pwd(k=20, choices=string.ascii_letters + string.digits):
    return "".join(random.choices(choices, k=k))


def encode_utf8(string):
    return string.encode("utf-8")


def filter_none_one(el):
    # for use with *args
    return filter(None, (el,))


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
        case {"private_key": private_key, "private_key_pwd": private_key_pwd, **rest}:
            assert isinstance(private_key, str)
            kwargs = rest | {
                "private_key": decrypt_private_bytes_snowflake(
                    encode_utf8(private_key), private_key_pwd
                )
            }
        case {"private_key": private_key, **rest}:
            assert isinstance(private_key, bytes)
            # ctor will fail if other than unencrypted DER format (bytes)
            SnowflakeKeypair.from_bytes_der(private_key)
        case _:
            raise ValueError(f"`private_key` not found in kwargs: {tuple(kwargs)}")
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


@dataclass(frozen=True)
class SnowflakeKeypair:
    private_key: rsa.RSAPrivateKey
    private_key_pwd: str = field(default_factory=make_private_key_pwd, repr=False)
    prefix = snowflake_env_var_prefix
    default_path = default_env_path

    __post_init__ = validate_dataclass_types

    def __eq__(self, other):
        us, them = (
            (type(el), el.private_key.private_numbers(), el.private_key_pwd)
            for el in (self, other)
        )
        return all(us_el == them_el for us_el, them_el in zip(us, them))

    def get_private_bytes(
        self, encoding=Encoding.PEM, format=PrivateFormat.PKCS8, encrypted=True
    ):
        return self.private_key.private_bytes(
            encoding=encoding,
            format=format,
            encryption_algorithm=BestAvailableEncryption(
                encode_utf8(self.private_key_pwd)
            )
            if encrypted
            else NoEncryption(),
        )

    @property
    def private_bytes(self):
        return self.get_private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encrypted=True,
        )

    @property
    def private_str(self):
        return self.private_bytes.decode("ascii")

    @property
    def private_str_unencrypted(self):
        return self.get_private_bytes(encrypted=False).decode("ascii")

    @property
    def public_key(self):
        return self.private_key.public_key()

    @property
    def public_bytes(self):
        return self.public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo,
        )

    @property
    def public_str(self):
        return self.public_bytes.decode("ascii")

    def with_password(self, private_key_pwd):
        return replace(self, private_key_pwd=private_key_pwd)

    def to_envrc(
        self,
        path: Optional[Path] = default_path,
        prefix: str = prefix,
        encrypted: bool = True,
    ):
        from snowflake_keypair_helper.con_utils import make_env_name

        names_fields = (
            (
                ("private_key", "private_str"),
                ("public_key", "public_str"),
                ("private_key_pwd", "private_key_pwd"),
            )
            if encrypted
            else (
                ("private_key", "private_str_unencrypted"),
                ("public_key", "public_str"),
            )
        )
        text = "\n".join(
            f"export {name}='{value}'"
            for name, value in (
                (
                    make_env_name(name, prefix=prefix),
                    getattr(self, field),
                )
                for (name, field) in names_fields
            )
        )
        if path is None:
            print(text)
        else:
            (path := Path(path)).write_text(text)
        return path

    @classmethod
    def generate(cls, password=None):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        return cls(private_key, *filter_none_one(password))

    @classmethod
    def from_bytes_pem(
        cls, private_bytes: bytes, private_key_pwd: Optional[str] = None
    ):
        private_key = load_pem_private_key(
            private_bytes,
            encode_utf8(private_key_pwd) if private_key_pwd else None,
        )
        return cls(private_key, *filter_none_one(private_key_pwd))

    @classmethod
    def from_bytes_der(
        cls, private_bytes: bytes, private_key_pwd: Optional[str] = None
    ):
        private_key = load_der_private_key(
            private_bytes,
            encode_utf8(private_key_pwd) if private_key_pwd else None,
        )
        return cls(private_key, *filter_none_one(private_key_pwd))

    from_bytes = from_bytes_pem

    @classmethod
    def from_str_pem(cls, private_str: str, private_key_pwd: Optional[str] = None):
        return cls.from_bytes(encode_utf8(private_str), private_key_pwd)

    from_str = from_str_pem

    @classmethod
    def from_environment(cls, ctx=os.environ, prefix=prefix):
        from snowflake_keypair_helper.con_utils import make_env_name

        kwargs = {
            field: ctx.get(make_env_name(name, prefix=prefix))
            for field, name in (
                ("private_str", "private_key"),
                ("private_key_pwd", "private_key_pwd"),
            )
        }
        return cls.from_str_pem(**kwargs)

    @classmethod
    def from_envrc(cls, path=default_path, prefix=prefix):
        from snowflake_keypair_helper.env_utils import parse_env_file

        ctx = parse_env_file(path)
        return cls.from_environment(ctx=ctx, prefix=prefix)

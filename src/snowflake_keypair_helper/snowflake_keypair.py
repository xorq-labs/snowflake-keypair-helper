import os
from dataclasses import (
    dataclass,
    field,
    replace,
)
from pathlib import Path
from typing import Optional

import cryptography.hazmat.primitives.asymmetric.rsa as rsa
import toolz
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
    default_env_path,
    snowflake_connection_name_formatter,
    snowflake_env_var_prefix,
)
from snowflake_keypair_helper.utils.dataclass_utils import (
    validate_dataclass_types,
)
from snowflake_keypair_helper.utils.general_utils import (
    decode_ascii,
    encode_utf8,
    ensure_header_footer,
    filter_none_one,
    make_oneline,
    make_private_key_pwd,
)


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
        return decode_ascii(self.private_bytes)

    @property
    def private_str_unencrypted(self):
        return decode_ascii(self.get_private_bytes(encrypted=False))

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
        return decode_ascii(self.public_bytes)

    def with_password(self, private_key_pwd):
        return replace(self, private_key_pwd=private_key_pwd)

    def to_dict(
        self,
        prefix: str = prefix,
        encrypted: bool = True,
        oneline: bool = True,
    ):
        from snowflake_keypair_helper.utils.con_utils import make_env_name

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
        dct = {
            make_env_name(name, prefix=prefix): getattr(self, field)
            for (name, field) in names_fields
        }
        if oneline:
            dct = toolz.valmap(make_oneline, dct)
        return dct

    def to_env_text(
        self,
        prefix: str = prefix,
        encrypted: bool = True,
        export: bool = False,
        oneline: bool = True,
    ):
        env_text = "\n".join(
            f"{'export ' if export else ''}{name}='{value}'"
            for name, value in self.to_dict(
                prefix=prefix, encrypted=encrypted, oneline=oneline
            ).items()
        )
        return env_text

    def to_env_path(
        self,
        path: Optional[Path] = default_path,
        prefix: str = prefix,
        encrypted: bool = True,
        export: bool = False,
        oneline: bool = True,
    ):
        env_text = self.to_env_text(
            prefix=prefix, encrypted=encrypted, export=export, oneline=oneline
        )
        if path is None:
            print(env_text)
        else:
            (path := Path(path)).write_text(env_text)
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
        encoded = encode_utf8(
            ensure_header_footer(private_str, private_key_pwd=private_key_pwd)
        )
        return cls.from_bytes(encoded, private_key_pwd)

    from_str = from_str_pem

    @classmethod
    def from_environment(cls, ctx=os.environ, prefix=prefix):
        from snowflake_keypair_helper.utils.con_utils import make_env_name

        kwargs = {
            field: ctx.get(make_env_name(name, prefix=prefix))
            for field, name in (
                ("private_str", "private_key"),
                ("private_key_pwd", "private_key_pwd"),
            )
        }
        return cls.from_str_pem(**kwargs)

    @classmethod
    def from_connection_name(cls, connection_name, ctx=os.environ):
        prefix = snowflake_connection_name_formatter.format(
            connection_name=connection_name
        )
        return cls.from_environment(ctx=ctx, prefix=prefix)

    @classmethod
    def from_env_path(cls, path=default_path, prefix=prefix):
        from snowflake_keypair_helper.utils.env_utils import parse_env_path

        ctx = parse_env_path(path)
        return cls.from_environment(ctx=ctx, prefix=prefix)

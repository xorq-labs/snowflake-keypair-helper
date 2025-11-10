import base64
import hashlib
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from functools import partial

import attr.setters as setters
import cryptography.hazmat.primitives.asymmetric.rsa as rsa
import jwt
import requests
from attr import (
    define,
    evolve,
    field,
)
from attr.validators import (
    instance_of,
    optional,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_der_private_key,
)
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat


try:
    from typing import Text
except ImportError:
    from typing_extensions import Text


def prepare_account_name_for_jwt(account: Text) -> Text:
    """
    Prepare the account identifier for use in the JWT.
    For the JWT, the account identifier must not include the subdomain or any region or cloud provider information.
    :param raw_account: The specified account identifier.
    :return: The account identifier in a form that can be used to generate the JWT.
    """
    split_on = "-" if ".global" in account else "."
    return account.upper().split(split_on)[0]


@define(on_setattr=setters.frozen)
class JWTGenerator:
    """
    Creates and signs a JWT with the specified private key, username, and account identifier. The JWTGenerator keeps the
    generated token and only regenerates the token if a specified period of time has passed.
    """

    LIFETIME = timedelta(minutes=59)  # The tokens will have a 59-minute lifetime
    RENEWAL_DELTA = timedelta(minutes=54)  # Tokens will be renewed after 54 minutes
    ALGORITHM = "RS256"  # Tokens will be generated using RSA with SHA256

    account: Text = field(
        validator=instance_of(Text), converter=prepare_account_name_for_jwt
    )
    user: Text = field(validator=instance_of(Text), converter=str.upper)
    private_key: Text = field(validator=instance_of(rsa.RSAPrivateKey))
    lifetime: timedelta = field(validator=instance_of(timedelta), default=LIFETIME)
    renewal_delay: timedelta = field(
        validator=instance_of(timedelta), default=RENEWAL_DELTA
    )
    # only renew_time and token can be mutated
    renew_time = field(
        validator=optional(instance_of(datetime)),
        factory=partial(datetime.now, timezone.utc),
        on_setattr=setters.NO_OP,
    )
    token = field(
        validator=optional(instance_of(Text)), default=None, on_setattr=setters.NO_OP
    )
    auth_url = field(
        validator=optional(instance_of(Text)), default=None, on_setattr=setters.NO_OP
    )
    endpoint = field(
        validator=optional(instance_of(Text)), default=None, on_setattr=setters.NO_OP
    )
    role = field(
        validator=optional(instance_of(Text)), default=None, on_setattr=setters.NO_OP
    )

    def __attrs_post_init__(self):
        if self.renewal_delay > self.lifetime:
            raise ValueError(
                "renewal_delay must be less than or equal to lifetime but {self.renewal_delay} > {self.lifetime}"
            )

    @property
    def qualified_username(self):
        return self.account + "." + self.user

    @property
    def public_key_fp(self):
        # Generate the public key fingerprint for the issuer in the payload.
        return self.calculate_public_key_fingerprint(self.private_key)

    def generate_token(self, now) -> Text:
        # Create our payload
        payload = {
            # Set the issuer to the fully qualified username concatenated with the public key fingerprint.
            "iss": self.qualified_username + "." + self.public_key_fp,
            # Set the subject to the fully qualified username.
            "sub": self.qualified_username,
            # Set the issue time to now.
            "iat": now,
            # Set the expiration time, based on the lifetime specified for this object.
            "exp": now + self.lifetime,
        }
        # Regenerate the actual token
        token = jwt.encode(
            payload, key=self.private_key, algorithm=JWTGenerator.ALGORITHM
        )
        # If you are using a version of PyJWT prior to 2.0, jwt.encode returns a byte string instead of a string.
        # If the token is a byte string, convert it to a string.
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        self.renew_time = now + self.renewal_delay
        self.token = token

    def get_token(self) -> Text:
        """
        Generates a new JWT. If a JWT has already been generated earlier, return the previously generated token unless the
        specified renewal time has passed.
        :return: the new token
        """
        now = datetime.now(timezone.utc)
        if self.token is None or self.renew_time <= now:
            # If the token has expired or doesn't exist, generate a new token.
            self.generate_token(now)
        return self.token

    def get_jwt(self, auth_url, endpoint, role=None) -> Text:
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "scope": endpoint if role is None else f"session:role:{role} {endpoint}",
            "assertion": self.get_token(),
        }
        response = requests.post(auth_url, data=data)
        response.raise_for_status()
        assert 200 == response.status_code, "unable to get snowflake token"
        return response.text

    def get_auth_headers(self, auth_url=None, endpoint=None, role=None) -> dict:
        jwt = self.get_jwt(
            auth_url or self.auth_url, endpoint or self.endpoint, role=role or self.role
        )
        headers = {"Authorization": f'Snowflake Token="{jwt}"'}
        return headers

    evolve = evolve

    @classmethod
    def from_text(cls, text, passphrase=None, **kwargs):
        private_key = load_pem_private_key(
            text.encode(),
            passphrase.encode() if passphrase else None,
            default_backend(),
        )
        return cls(private_key=private_key, **kwargs)

    @classmethod
    def from_path(cls, path, **kwargs):
        text = path.read_text()
        return cls.from_text(text, **kwargs)

    @classmethod
    def from_con(cls, con, **kwargs):
        def wrap_pem_private_key(text):
            dashes, typ = "-----", "PRIVATE KEY"
            (header, footer) = (
                f"{dashes}{which} {typ}{dashes}" for which in ("BEGIN", "END")
            )
            wrapped = "\n".join((header, text, footer))
            return wrapped

        from_con = {
            "account": con.account,
            "user": con.user,
            "auth_url": f"https://{con.host}/oauth/token",
            "role": con.role,
        }
        if con._private_key:
            match con._private_key:
                case bytes():
                    private_key = load_der_private_key(con._private_key, None)
                case str():
                    private_key = load_pem_private_key(
                        wrap_pem_private_key(con._private_key).encode(), None
                    )
                case _:
                    raise ValueError
            return cls(private_key=private_key, **from_con | kwargs)
        elif con._private_key_file:
            return cls.from_path(
                con._private_key_file,
                passphrase=con._private_key_file_pwd,
                **from_con | kwargs,
            )
        else:
            raise ValueError

    @staticmethod
    def calculate_public_key_fingerprint(private_key: rsa.RSAPrivateKey) -> Text:
        """
        Given a private key in PEM format, return the public key fingerprint.
        :param private_key: private key string
        :return: public key fingerprint
        """
        # Get the sha256 hash of the raw bytes.
        sha256hash = hashlib.sha256(
            private_key.public_key().public_bytes(
                Encoding.DER, PublicFormat.SubjectPublicKeyInfo
            )
        )

        # Base64-encode the value and prepend the prefix "SHA256:".
        public_key_fp = "SHA256:" + base64.b64encode(sha256hash.digest()).decode(
            "utf-8"
        )
        return public_key_fp

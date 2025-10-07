import pytest
from cryptography.hazmat.primitives.serialization import (
    # BestAvailableEncryption,
    Encoding,
    # NoEncryption,
    PrivateFormat,
    # PublicFormat,
    # load_der_private_key,
    # load_pem_private_key,
)

from snowflake_keypair_helper.crypto_utils import (
    SnowflakeKeypair,
)


def test_password_non_none():
    keypair = SnowflakeKeypair.generate(password=None)
    assert keypair.private_key_pwd is not None


def test_eq():
    keypairs = (keypair0, keypair1) = tuple(
        SnowflakeKeypair.generate(password=password)
        for password in ("password0", "password1")
    )
    assert len(set(keypair.private_key_pwd for keypair in keypairs)) > 1
    assert keypair0 == keypair0 and keypair1 == keypair1
    assert keypair0 != keypair1


def test_invalid_pwd():
    keypairs = (keypair0, keypair1) = tuple(
        SnowflakeKeypair.generate(password=password)
        for password in ("password0", "password1")
    )
    assert len(set(keypair.private_key_pwd for keypair in keypairs)) > 1
    with pytest.raises(ValueError, match="Incorrect password, could not decrypt key"):
        SnowflakeKeypair.from_bytes(
            keypair0.private_bytes,
            keypair1.private_key_pwd,
        )


def test_from_bytes():
    keypair0 = SnowflakeKeypair.generate()
    keypair1 = SnowflakeKeypair.from_bytes(
        keypair0.private_bytes,
        keypair0.private_key_pwd,
    )
    assert keypair0 == keypair1


def test_from_str():
    keypair0 = SnowflakeKeypair.generate()
    keypair1 = SnowflakeKeypair.from_str(
        keypair0.private_str,
        keypair0.private_key_pwd,
    )
    keypair2 = SnowflakeKeypair.from_str_pem(
        keypair0.private_str,
        keypair0.private_key_pwd,
    )
    assert keypair0 == keypair1
    assert keypair0 == keypair2


def test_varying_encrypted_private_bytes():
    keypair = SnowflakeKeypair.generate()
    assert keypair.private_bytes != keypair.private_bytes


def test_varying_encrypted_private_bytes_but_same_private_numbers():
    keypair0 = SnowflakeKeypair.generate()
    keypair1 = SnowflakeKeypair(keypair0.private_key, keypair0.private_key_pwd)
    assert keypair0 == keypair1 and keypair0.private_bytes != keypair1.private_bytes


def test_unecrypted_same_private_str():
    keypair = SnowflakeKeypair.generate()
    actual = keypair.private_str_unencrypted
    expected = keypair.get_private_bytes(
        encoding=Encoding.PEM, format=PrivateFormat.PKCS8, encrypted=False
    ).decode("ascii")
    assert actual == expected


@pytest.mark.parametrize(
    "encoding,ctor",
    (
        (Encoding.DER, SnowflakeKeypair.from_bytes_der),
        (Encoding.PEM, SnowflakeKeypair.from_bytes_pem),
        (Encoding.PEM, SnowflakeKeypair.from_bytes),
    ),
)
def test_unecrypted_roundtrip(encoding, ctor):
    keypair0 = SnowflakeKeypair.generate()
    unencrypted_bytes = keypair0.get_private_bytes(
        encoding=encoding, format=PrivateFormat.PKCS8, encrypted=False
    )
    keypair1 = ctor(unencrypted_bytes).with_password(keypair0.private_key_pwd)
    assert keypair0 == keypair1


@pytest.mark.parametrize(
    "encoding,ctor",
    (
        (Encoding.DER, SnowflakeKeypair.from_bytes_der),
        (Encoding.PEM, SnowflakeKeypair.from_bytes_pem),
    ),
)
def test_ecrypted_roundtrip(encoding, ctor):
    keypair0 = SnowflakeKeypair.generate()
    encrypted_bytes = keypair0.get_private_bytes(
        encoding=encoding, format=PrivateFormat.PKCS8, encrypted=True
    )
    keypair1 = ctor(encrypted_bytes, keypair0.private_key_pwd)
    assert keypair0 == keypair1


def test_roundtrip_envrc(tmp_path):
    env_path = tmp_path.joinpath(".env")
    expected = SnowflakeKeypair.generate()
    expected.to_envrc(env_path)
    actual = SnowflakeKeypair.from_envrc(env_path)
    assert actual == expected

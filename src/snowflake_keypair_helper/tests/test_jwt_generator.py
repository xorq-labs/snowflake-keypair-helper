from datetime import timedelta
from time import sleep

import pytest

from snowflake_keypair_helper.api import (
    SnowflakeKeypair,
    connect_env_keypair,
)
from snowflake_keypair_helper.jwt_generator import JWTGenerator


@pytest.fixture
def con():
    con = connect_env_keypair()
    return con


def test_from_text(con):
    kp = SnowflakeKeypair.from_environment()
    jwt_generator = JWTGenerator.from_text(
        text=kp.private_str,
        passphrase=kp.private_key_pwd,
        account=con.account,
        user=con.user,
    )
    token = jwt_generator.get_token()
    assert token


def test_from_path_encrypted(con, tmp_path):
    path = tmp_path.joinpath("tmp")
    kp = SnowflakeKeypair.from_environment()
    path.write_text(kp.private_str)
    jwt_generator = JWTGenerator.from_path(
        path=path,
        passphrase=kp.private_key_pwd,
        account=con.account,
        user=con.user,
    )
    token = jwt_generator.get_token()
    assert token


def test_from_con(con):
    jwt_generator = JWTGenerator.from_con(con)
    token = jwt_generator.get_token()
    assert token


def test_renewal_delay_condition(con):
    duration = 60
    with pytest.raises(
        ValueError, match="renewal_delay must be less than or equal to lifetime but"
    ):
        JWTGenerator.from_con(
            con, lifetime=timedelta(duration), renewal_delay=timedelta(duration + 1)
        )


@pytest.mark.parametrize("duration", (1, 2))
def test_lifetime_exceeded(con, duration):
    jwt_generator = JWTGenerator.from_con(
        con,
        lifetime=timedelta(seconds=duration),
        renewal_delay=timedelta(seconds=duration),
    )
    token0 = jwt_generator.get_token()
    sleep(duration + 0.01)
    token1 = jwt_generator.get_token()
    assert token0 != token1


@pytest.mark.parametrize("duration", (60,))
def test_lifetime_not_exceeded(con, duration):
    jwt_generator = JWTGenerator.from_con(
        con,
        lifetime=timedelta(seconds=duration),
        renewal_delay=timedelta(seconds=duration),
    )
    token0 = jwt_generator.get_token()
    sleep(1)
    token1 = jwt_generator.get_token()
    assert token0 == token1

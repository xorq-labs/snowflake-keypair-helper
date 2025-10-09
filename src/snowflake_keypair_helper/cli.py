import importlib
from os import devnull
from pathlib import Path

import click

from snowflake_keypair_helper.con_utils import (
    assign_public_key as _assign_public_key,
    connect_env,
)
from snowflake_keypair_helper.constants import (
    snowflake_env_var_prefix,
)
from snowflake_keypair_helper.crypto_utils import (
    SnowflakeKeypair,
)
from snowflake_keypair_helper.init_state_utils import (
    create_user as _create_user,
)


def public_key_from_path(path, prefix=snowflake_env_var_prefix):
    from snowflake_keypair_helper.env_utils import parse_env_file
    from snowflake_keypair_helper.con_utils import make_env_name

    dct = parse_env_file(path)
    public_key = dct[make_env_name("PUBLIC_KEY", prefix=prefix)]
    return public_key


def arbitrate_public_key(
    public_key_str=None, path=None, prefix=snowflake_env_var_prefix
):
    match (path, public_key_str):
        case [None, None]:
            raise ValueError("one and only one value must be non None")
        case [str() | Path(), None]:
            return public_key_from_path(path, prefix=prefix)
        case [None, str()]:
            return public_key_str
        case _:
            raise ValueError("improper types pass")


def gen_commands():
    commands = (
        value
        for value in importlib.import_module(__name__).__dict__.values()
        if isinstance(value, click.Command)
    )
    yield from commands


@click.command(help="generate a new keypair and write it to disk")
@click.argument("path")
@click.option("--password", default=None)
@click.option("--prefix", default=snowflake_env_var_prefix)
@click.option("--encrypted/--no-encrypted", default=True)
def generate_keypair(
    path,
    password=None,
    prefix=snowflake_env_var_prefix,
    encrypted=True,
):
    path = None if path == "-" else Path(path)
    keypair = SnowflakeKeypair.generate(password=password)
    path = keypair.to_envrc(path=path, prefix=prefix, encrypted=encrypted)
    return path


@click.command(help="assign a public key to a user")
@click.argument("user")
@click.option("--public_key_str", default=None)
@click.option("--path", default=None)
@click.option("--envrc-path", default=devnull)
def assign_public_key(user, public_key_str=None, path=None, envrc_path=devnull):
    public_key_str = arbitrate_public_key(public_key_str=public_key_str, path=path)
    con = connect_env(envrc_path=envrc_path)
    _assign_public_key(con, user, public_key_str, assert_value=True)


@click.command(help="create a user")
@click.argument("user")
@click.option("--envrc-path", default=devnull)
def create_user(user, envrc_path=devnull):
    con = connect_env(envrc_path=envrc_path)
    _create_user(con, user)


@click.command(help=f"list all commands available from this cli ({__package__})")
def list_cli_commands():
    print(
        "\n".join(
            f"{command.name}: {command.help if command.help else 'no help string specified'}"
            for command in gen_commands()
        )
    )

import importlib
from os import devnull
from pathlib import Path

import click

from snowflake_keypair_helper.con_utils import (
    assign_public_key as _assign_public_key,
    connect_env_envrc,
    generate_and_assign_keypair as _generate_and_assign_keypair,
)
from snowflake_keypair_helper.constants import (
    snowflake_env_var_prefix,
)
from snowflake_keypair_helper.crypto_utils import (
    SnowflakeKeypair,
)


def gen_commands():
    commands = (
        value
        for value in importlib.import_module(__name__).__dict__.values()
        if isinstance(value, click.Command)
    )
    yield from commands


@click.command(help="generate a new public key and write it to the given path")
@click.argument("path")
@click.option("--password", default=None)
@click.option("--prefix", default=snowflake_env_var_prefix)
@click.option("--encrypted/--no-encrypted", default=True)
def generate_envrc(
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
@click.argument("public_key_str")
@click.option("--envrc-path", default=devnull)
def assign_public_key(user, public_key_str, envrc_path=devnull):
    con = connect_env_envrc(envrc_path)
    _assign_public_key(con, user, public_key_str, assert_value=True)


@click.command(
    help="generate a new keypair, write it to disk and assign the public key to a user"
)
@click.argument("user")
@click.option("--path", default=None)
@click.option("--envrc-path", default=devnull)
def generate_and_assign_keypair(user, path=None, envrc_path=devnull):
    con = connect_env_envrc(envrc_path)
    _generate_and_assign_keypair(con, user, path=path)


@click.command(help=f"list all commands available from this cli ({__package__})")
def list_cli_commands():
    print(
        "\n".join(
            f"{command.name}: {command.help if command.help else 'no help string specified'}"
            for command in gen_commands()
        )
    )

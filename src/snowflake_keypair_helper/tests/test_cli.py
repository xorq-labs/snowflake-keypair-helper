import re
from subprocess import (
    Popen,
    PIPE,
)

import pytest

from snowflake_keypair_helper.cli import (
    gen_commands,
)
from snowflake_keypair_helper.constants import (
    snowflake_env_var_prefix,
    gh_test_user,
)
from snowflake_keypair_helper.env_utils import (
    parse_env_path,
)


all_cli_command_names = tuple(command.name for command in gen_commands())


def do_popen_communicate(*args, do_decode=True):
    popened = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = popened.communicate()
    return (popened.returncode, out.decode("ascii"), err.decode("ascii"), popened)


@pytest.mark.benchmark
@pytest.mark.parametrize("command", all_cli_command_names)
def test_cli_helps(command, tmp_path):
    (returncode, out, err, _) = do_popen_communicate(command, "--help")
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    assert out.startswith(f"Usage: {command} ")


@pytest.mark.benchmark
def test_cli_generate_keypair_path(tmp_path, monkeypatch):
    # writes to cwd, not stdout/stderr
    monkeypatch.chdir(tmp_path)
    name = "my.env"
    (returncode, out, err, _) = do_popen_communicate("skh-generate-keypair", name)
    assert not returncode
    assert not err
    assert not out
    (path, *rest) = tmp_path.iterdir()
    assert not rest
    assert path.name == name
    path.unlink()


@pytest.mark.benchmark
def test_cli_generate_keypair_stdout(tmp_path, monkeypatch):
    # writes to stdout, not cwd/stderr
    monkeypatch.chdir(tmp_path)
    name = "-"
    (returncode, out, err, _) = do_popen_communicate("skh-generate-keypair", name)
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    path = tmp_path.joinpath("my.env")
    path.write_text(out)
    dct = parse_env_path(path)
    assert dct
    assert all(key.startswith(snowflake_env_var_prefix) for key in dct)
    path.unlink()


@pytest.mark.benchmark
def test_cli_list_cli_commands(tmp_path, monkeypatch):
    # writes to stdout, not cwd/stderr
    monkeypatch.chdir(tmp_path)
    (returncode, out, err, _) = do_popen_communicate("skh-list-cli-commands")
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    assert all(command.name in out for command in gen_commands())


@pytest.mark.benchmark
def test_assign_public_key_no_args():
    command = "skh-assign-public-key"
    returncode, _, err, _ = do_popen_communicate(command, gh_test_user)
    assert returncode != 0
    infix = "one and only one value must be non None"
    assert re.match(f".*{infix}.*", err, re.DOTALL), err


@pytest.mark.parametrize("args", (("--oneline",), ("--no-oneline",), ()))
def test_assign_public_key_from_path(args, tmp_path, monkeypatch):
    # writes to stdout, not cwd/stderr
    monkeypatch.chdir(tmp_path)
    name = "-"
    (returncode, out, err, _) = do_popen_communicate(
        "skh-generate-keypair", name, *args
    )
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    path = tmp_path.joinpath("my.env")
    path.write_text(out)

    command = "skh-assign-public-key"
    returncode, out, err, _ = do_popen_communicate(
        command, gh_test_user, "--path", str(path)
    )
    assert returncode == 0

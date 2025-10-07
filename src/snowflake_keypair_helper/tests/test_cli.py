import pytest
from subprocess import (
    Popen,
    PIPE,
)

from snowflake_keypair_helper.cli import (
    gen_commands,
)
from snowflake_keypair_helper.constants import (
    snowflake_env_var_prefix,
)
from snowflake_keypair_helper.env_utils import (
    parse_env_file,
)


all_cli_command_names = tuple(command.name for command in gen_commands())


def do_popen_communicate(*args, do_decode=True):
    popened = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = popened.communicate()
    return (popened.returncode, out.decode("ascii"), err.decode("ascii"), popened)


@pytest.mark.parametrize("command", all_cli_command_names)
def test_cli_helps(command, tmp_path):
    (returncode, out, err, _) = do_popen_communicate(command, "--help")
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    assert out.startswith(f"Usage: {command} ")


def test_cli_generate_keypair_path(tmp_path, monkeypatch):
    # writes to cwd, not stdout/stderr
    monkeypatch.chdir(tmp_path)
    name = "my.envrc"
    (returncode, out, err, _) = do_popen_communicate("generate-keypair", name)
    assert not returncode
    assert not err
    assert not out
    (path, *rest) = tmp_path.iterdir()
    assert not rest
    assert path.name == name


def test_cli_generate_keypair_stdout(tmp_path, monkeypatch):
    # writes to stdout, not cwd/stderr
    monkeypatch.chdir(tmp_path)
    name = "-"
    (returncode, out, err, _) = do_popen_communicate("generate-keypair", name)
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    path = tmp_path.joinpath("my.envrc")
    path.write_text(out)
    dct = parse_env_file(path)
    assert dct
    assert all(key.startswith(snowflake_env_var_prefix) for key in dct)


def test_cli_list_cli_commands(tmp_path, monkeypatch):
    # writes to stdout, not cwd/stderr
    monkeypatch.chdir(tmp_path)
    (returncode, out, err, _) = do_popen_communicate("list-cli-commands")
    assert not returncode
    assert not err
    assert not tuple(tmp_path.iterdir())
    assert all(command.name in out for command in gen_commands())

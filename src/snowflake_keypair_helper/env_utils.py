import os
import contextlib
import itertools
import re
import shlex
from unittest import mock
from pathlib import Path


compiled_env_var_setting_re = re.compile(
    "(?:export )?([^=]+)=(.*)",
    flags=re.DOTALL,
)


def parse_env_file(env_file, compiled_re=compiled_env_var_setting_re):
    def gen_shlex_lines(path):
        def make_lexer(path):
            lex = shlex.shlex(Path(path).read_text(), posix=True)
            lex.whitespace_split = True
            return lex

        def get_before_token_after(lexer):
            return (lexer.lineno, lexer.get_token(), lexer.lineno)

        tokens = ()
        for before, token, after in map(
            get_before_token_after,
            itertools.repeat(make_lexer(path)),
        ):
            if token is None:
                if tokens:
                    # single line env file never triggers `before != after`
                    yield " ".join(tokens)
                break
            tokens += (token,)
            if before != after:
                yield " ".join(tokens)
                tokens = ()

    matches = map(
        compiled_re.match,
        gen_shlex_lines(env_file),
    )
    dct = dict(match.groups() for match in filter(None, matches))
    return dct


@contextlib.contextmanager
def with_environ(dct, clear=False):
    # https://stackoverflow.com/a/51754362
    with mock.patch.dict(os.environ, dct, clear=clear):
        yield


@contextlib.contextmanager
def with_envrc(envrc_path, clear=False):
    dct = parse_env_file(envrc_path)
    with mock.patch.dict(os.environ, dct, clear=clear):
        yield

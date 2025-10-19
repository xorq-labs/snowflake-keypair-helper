# snowflake-keypair-helper

a library and CLI tool for creating, managing and using keypairs to authenticate to [Snowflake](www.snowflake.com)

---

## why?
snowflake is phasing out password-only authentication. recently, snowflake
tightened defaults: new accounts (since the 2024_08 release bundle) enforce mfa
enrollment by default for human users. more info in [snowflake
docs](https://docs.snowflake.com/en/release-notes/bcr-bundles/2024_08/bcr-1784)

additionally, the information i was able to find was:
- dispered among various pages
- does not demonstrate a unified way to do things
- does not do so in pure python

finally, adbc_driver_manager.dbapi.Connection requires a different encoding
(encrypted, DER encoded) than SnowflakeConnection (unencrypted, PEM encoded)
and how to do the conversion is not easily discoverable.

## how?

using [pyca/cryptography](https://github.com/pyca/cryptography), this repo provides a pure python based way of creating, managing and using keypairs along with helpers to serialize/deserialize them to/from disk as well as loading them from environment variables.

notably, this library uses itself to test `GH_USER`'s ability to set `GH_TEST_USER`'s keypair.

---

## quickstart

### option 1: install via pip

Get it via pip:

```bash
pip install snowflake-keypair-helper
```

Use the CLI tool:

```bash
generate-keypair          # generate a new keypair and write it to disk
assign-public-key         # assign a public key to a user
create-user               # create a user
list-cli-commands         # list all commands available from this cli (snowflake_keypair_helper)
```

### Option 2: Run via nix

```bash
nix run github:xorq-labs/snowflake-keypair-helper#list-cli-commands
```

### Option 3: run directly from uv
```
uv run --isolated --with snowflake-keypair-helper list-cli-commands
```

### Option 4: Initialize an environment with uv

First, clone the repository:

```bash
git clone git@github.com:xorq-labs/snowflake-keypair-helper.git
```

and cd into it:

```bash
# Create/refresh a local venv via uv
./with-uvenv              # (runs: uv run uv sync --all-groups)

# (Optional) Install pre-commit hooks
./with-uvenv uv run pre-commit install

# Show available CLI commands from this package
./with-uvenv uv run list-cli-commands
```

then, generate a keypair and assign it to a user:

```bash
generate-keypair alice.user.envrc
assign-public-key alice --path alice.user.envrc # alice is snowflake user name and assumes admin role
```

and then, connect using the keypair you've created:

```python
from snowflake_keypair_helper import connect_env_keypair
con = connect_env_keypair(envrc_path="alice.user.envrc")
```

---

## examples

### understanding .envrc files

.envrc files are simple KEY=VALUE files. they are convenient because:

- the CLI can read them with `--envrc-path` to fill in missing `SNOWFLAKE_*` values temporarily.
- if you use [direnv], you can `source_env` them to export variables in your shell automatically.

**important:** you should not commit secret-bearing files; keep them in `.gitignore` and restrict permissions.

#### example .envrc (developer defaults, non-secret)

```bash
export SNOWFLAKE_ACCOUNT="xy12345.us-east-1"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
export SNOWFLAKE_DATABASE="ANALYTICS"
export SNOWFLAKE_SCHEMA="PUBLIC"
export SNOWFLAKE_ROLE="PUBLIC"
```

#### example .envrc.secrets.snowflake.admin (admin creds)

```bash
# Admin identity that can set PUBLIC_KEY on users
export SNOWFLAKE_USER="admin_user"
export SNOWFLAKE_ROLE="ACCOUNTADMIN" # or "ORGADMIN"/"USERADMIN"
# export SNOWFLAKE_PRIVATE_KEY="<encrypted private key PEM block>"
# export SNOWFLAKE_PUBLIC_KEY="<corresponding public key PEM block>"
```

---

### as a developer, generate a new keypair and password

```bash
generate-keypair my-user
```

the keypair is serialized to disk in a file named `my-user`. after this, you can share the public key with your snowflake user admin to assign to your user.

### as a Snowflake admin, assign a public key from a file

```bash
# file should set a variable named SNOWFLAKE_PUBLIC_KEY
assign-public-key "$SNOWFLAKE_USER" --path "$SNOWFLAKE_ENVRC"
```

### as a Snowflake admin, assign a public key from an environment variable

```bash
# NOTE: we pass `--` so that `--` in args is not interpreted as a flag
assign-public-key -- "$USER" --public_key_str "$USER_PUBLIC_KEY"
```

the connection created to assign the public key gets its arguments from your environment variables, which default to `SNOWFLAKE_` prefixed variable names like `SNOWFLAKE_USER`.

if you need to supplement your environment variables, you can pass `--envrc-path` which is a path parsed for environment variables and temporarily added to the environment during the invocation (see below).

### as a developer, generate and assign a new keypair

```bash
path="$TEST_USER".envrc
generate-keypair "$path"
assign-public-key \
    "$TEST_USER" \
    --path "$path" \
    --envrc-path .envrc.secrets.snowflake.keypair
```

writing the variables to an env file (`"$TEST_USER".envrc`), using the developer's credentials loaded from disk (`.envrc.secrets.snowflake.keypair`). this is handy for users meant only for testing.

### as a developer, connect with the keypair variables you've populated to environment variables

```python
from snowflake_keypair_helper import connect_env_keypair

con = connect_env_keypair()
```

### as a developer, connect with the keypair you've created on disk

```python
from snowflake_keypair_helper.api import (
    connect_env_keypair,
)

con = connect_env_keypair(envrc_path="my-keypair.env")
```

---

## development

```bash
# create a local venv from bare python
./with-uvenv  # with no arguments: defaults to uv run uv sync --all-groups

# set up pre-commit
./with-uvenv uv run pre-commit install

# run ipython with a development install of the repo
./with-uvenv uv run ipython
```

---

## uv

you can drop into an ipython environment (non-editable install of the last pypi release) with:

```bash
uv run --isolated --with snowflake-keypair-helper,ipython ipython
```

each [`project.scripts`](https://github.com/xorq-labs/snowflake-keypair-helper/blob/main/pyproject.toml#L31-L34) entry is available as well:

```bash
uv run --isolated --with snowflake-keypair-helper list-cli-commands
```

---

## nix

you can drop into an ipython environment (non-editable install of the current `main`) with:

```bash
nix run github:xorq-labs/snowflake-keypair-helper
```

each [`project.scripts`](https://github.com/xorq-labs/snowflake-keypair-helper/blob/main/pyproject.toml#L31-L34) entry is available as well:

```bash
nix run github:xorq-labs/snowflake-keypair-helper#list-cli-commands
```

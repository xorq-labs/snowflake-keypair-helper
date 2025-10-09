# what?

a library and cli tool for creating, managing and using keypairs to authenticate to [Snowflake](www.snowflake.com)

# why?

the information i was able to find was
- dispered among various pages
- does not demonstrate a unified way to do things
- does not do so in pure python

additionally, `adbc_driver_manager.dbapi.Connection` requires a different encoding (encrypted, DER encoded) than `SnowflakeConnection` (unencrypted, PEM encoded) and how to do the conversion is not easily discoverable

# how?

using [pyca/cryptography](https://github.com/pyca/cryptography), this repo provides a pure python based way of creating, managing and using keypairs along with helpers to serialize/deserialize them to/from disk as well as loading then from environment variables

notably, this library uses itself to test `GH_USER`'s ability to set `GH_TEST_USER`'s keypair

---

# quickstart

initialize an environment with
```
./with-uvenv
```
this will bootstrap a venv by way of `uv run`

you can subsequently activate the venv with
```
source ./.venv/bin/activate
```
or use `./with-uvenv uv run $command` to run particular commands

---

# examples

### as a user, generate a new keypair and password
```
generate-keypair my-user
```
the keypair is serialized to disk in a file named my-user. after this, you can share the public key with your snowflake user admin to assign to your user

### as a user admin, assign a public key from a file
```
# file should set a variable named SNOWFLAKE_PUBLIC_KEY
assign-public-key "$USER" --path "$SNOWFLAKE_ENVRC"
```

### as a user admin, assign a public key from an environment variable
```
# NOTE: we pass `--` so that `--` in args is not interpreted as a flag

assign-public-key -- "$USER" --public_key_str "$USER_PUBLIC_KEY"
```
the connection created to assign the public key gets its arguments from your environment variables, which default to `SNOWFLAKE_` prefixed variables names like `SNOWFLAKE_USER`

if you need to supplement your environment variables, you can pass `--envrc-path` which is a path parsed for environment variables and temporarily added to the environment during the invocation (see below)

### as a developer, generate and assign a new keypair
```
path="$TEST_USER".envrc
generate-keypair "$path"
assign-public-key \
    "$TEST_USER" \
    --path "$path" \
    --envrc-path .envrc.secrets.snowflake.keypair
```
writing the variables to an env file (`"$TEST_USER".envrc`), using the developer's credentials loaded from disk (`.envrc.secrets.snowflake.keypair`). this is handy for users meant only for testing

---

# development

```
# create a local venv from bare python
./with-uvenv  # with no arguments: defaults to uv run uv sync --all-groups
# set up pre-commit
./with-uvev uv run pre-commit install
# run ipython with a development install of the repo
./with-uvev uv run ipython
```

---

# nix

you can drop into an ipython environment (non-editable install of the current `main`) with
```
nix run github:xorq-labs/snowflake-keypair-helper
```

each [`project.scripts`](https://github.com/xorq-labs/snowflake-keypair-helper/blob/main/pyproject.toml#L28-L32) entry is available as well
```
nix run github:xorq-labs/snowflake-keypair-helper#generate-keypair
```

# what?

a library and cli tool for creating, managing and using keypairs to authenticate to [Snowflake](www.snowflake.com)

# why?

the information i was able to find was
- dispered among various pages
- does not demonstrate a "single way" to do things
- and does not do so in pure python

additionally, `adbc_driver_manager.dbapi.Connection` requires a different type of key (encrypted, DER encoded) than `SnowflakeConnection` (unencrypted, PEM encoded)

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

you can subsequently use `./with-uvenv uv run $command` commands

you can also fall back to activating the venv with
```
source ./.venv/bin/activate
```

---

# examples

### as a user, generate a new keypair and password
```
generate-envrc my-user
```
the keypair is serialized to disk as a .env file. after this, you can share the public key with your snowflake user admin to assign to your user

### as a user admin, assign a public key
```
# NOTE: we pass `--` so that `--` in args is not interpreted as a flag

assign-public-key -- "$USER" "$SNOWFLAKE_PUBLIC_KEY"
```
the connection created to assign the public key gets its arguments from your environment variables, which default to `SNOWFLAKE_` prefixed variables names like `SNOWFLAKE_USER`

if you need to supplement your environment variables, you can pass `--envrc-path` which is parsed for environment variables and temporarily added to the environment during the invocation (see below)

### as a developer, generate and assign a new keypair
```
generate-and-assign-keypair \
    "$TEST_USER" \
    --path "$TEST_USER.envrc.secrets.snowflake.keypair" \
    --envrc-path .envrc.secrets.snowflake.keypair
```
writing the variables to an env file, using the developer's credentials loaded from disk. this is handy for users meant only for testing

---

# development

```
# create a local venv from bare python
./with-uvenv  # with no arguments: defaults to uv run uv sync --all-groups
# set up pre-commit
./with-uvev uv run pre-commit install
```

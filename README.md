# what?

a repository that demonstrates using and administering snowflake keypair authentication

# why?

the information that is available is both dispered among various pages and does not demonstrate a single way to do things. in particular, `adbc_driver_manager.dbapi.Connection` requires a different type of key than `SnowflakeConnection`

# how?

this repo provides a pure python based way of creating and managing keys along with helpers to serialize/deserialize them to/from disk as well as loading then from environment variables

initialize an environment with `./with-uvenv`. this will bootstrap an environment to use to `uv run` this project from. you can always fall back to the local environment with `source ./.venv/bin/activate`

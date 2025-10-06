from pathlib import Path


snowflake_env_var_prefix = "SNOWFLAKE_"

default_database = "SNOWFLAKE_SAMPLE_DATA"
default_schema = "TPCH_SF1"
default_env_path = Path(".envrc.secrets.snowflake.keypair")
default_warehouse = "COMPUTE_WH"


gh_user = "GH_USER"
gh_test_user = "GH_TEST_USER"
gh_test_role = "GH_TEST_ROLE"

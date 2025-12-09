import subprocess

import pytest


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "module",
    (
        "snowflake_keypair_helper",
        "snowflake_keypair_helper.api",
        "snowflake_keypair_helper.cli",
        "snowflake_keypair_helper.constants",
        "snowflake_keypair_helper.utils.con_utils",
        "snowflake_keypair_helper.utils.crypto_utils",
        "snowflake_keypair_helper.utils.dataclass_utils",
        "snowflake_keypair_helper.utils.env_utils",
        "snowflake_keypair_helper.utils.init_state_utils",
    ),
)
def test_benchmark_module_import(module):
    subprocess.check_output(
        (
            "python",
            "-c",
            f"import {module}",
        )
    )

"""Testing for the config module."""
from unittest import mock

from djtools.configs.config import BaseConfig


def test_baseconfig_aws_profile():
    """Test for the BaseConfig class."""
    BaseConfig()


@mock.patch(
    "inspect.stack",
    new=mock.Mock(
        return_value=[
            "", "", ["", "", "", "build_config"], ["", "bin/djtools"]
        ],
    )
)
def test_baseconfig_limits_repr_in_cli_execution():
    """Test for the BaseConfig class."""
    BaseConfig(key="value")

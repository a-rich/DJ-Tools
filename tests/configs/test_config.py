"""Testing for the config module."""
from unittest import mock

from djtools.configs.config import BaseConfig
from djtools.utils.config import UtilsConfig


@mock.patch(
    "inspect.stack",
    new=mock.Mock(
        return_value=[
            "",
            "",
            ["", "", "", "build_config"],
            ["", "bin/djtools"],
        ],
    ),
)
def test_baseconfig_limits_repr_in_cli_execution():
    """Test for the BaseConfig class."""
    BaseConfig(key="value")


def test_baseconfig_repr_differentiates_baseconfig_and_subclasses():
    """Test for the BaseConfig class."""
    base_config = BaseConfig()
    utils_config = UtilsConfig()
    assert "LOG_LEVEL=INFO\n\tVERBOSITY=0" in repr(base_config)
    assert "LOG_LEVEL=INFO\n\tVERBOSITY=0" not in repr(utils_config)

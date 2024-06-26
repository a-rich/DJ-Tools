"""Testing for the config module."""

from unittest import mock

import pytest

from djtools.configs.config import BaseConfig
from djtools.spotify.config import SpotifyConfig


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
    spotify_config = SpotifyConfig()
    assert "LOG_LEVEL=INFO\n\tVERBOSITY=0" in repr(base_config)
    assert "LOG_LEVEL=INFO\n\tVERBOSITY=0" not in repr(spotify_config)


@pytest.mark.parametrize("num_elements", [2, 4, 6])
def test_baseconfig_repr_indents_lists(num_elements):
    """Test for the BaseConfig class."""
    list_elements = [{"name": "thing"}] * num_elements
    spotify_config = SpotifyConfig(SPOTIFY_PLAYLIST_SUBREDDITS=list_elements)
    repr_string = repr(spotify_config)
    assert repr_string.count("\n\t\t") == len(list_elements)

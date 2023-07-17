"""Testing for the config module."""
import os
import re

import pytest

from djtools.utils.config import UtilsConfig


def test_utilsconfig(caplog):
    """Test the UtilsConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "CHECK_TRACKS": True,
        "CHECK_TRACKS_SPOTIFY_PLAYLISTS": ["playlist"],
        "AWS_PROFILE": "default",
    }
    UtilsConfig(**cfg)
    assert caplog.records[0].message == (
        "CHECK_TRACKS depends on valid Spotify API credentials in "
        "SpotifyConfig."
    )


def test_utilsconfig_aws_profile_not_set():
    """Test for the UtilsConfig class."""
    cfg = {"CHECK_TRACKS": True}
    os.environ["AWS_PROFILE"] = ""
    with pytest.raises(
        RuntimeError, match=re.escape(
            "Without AWS_PROFILE set to a valid profile ('default' or otherwise) "
            "you cannot use the CHECK_TRACKS feature"
        ),
    ):
        UtilsConfig(**cfg)

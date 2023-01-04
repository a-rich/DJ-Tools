import pytest

from djtools.utils.config import UtilsConfig


def test_utilsconfig():
    cfg = {"CHECK_TRACKS": True, "AWS_PROFILE": "default"}
    UtilsConfig(**cfg)


def test_utilsconfig_no_aws_profile():
    cfg = {"CHECK_TRACKS": True, "AWS_PROFILE": ""}
    with pytest.raises(
        ValueError, match="Config must include AWS_PROFILE for CHECK_TRACKS",
    ):
        UtilsConfig(**cfg)


def test_utilsconfig_no_spotify_credentials():
    cfg = {
        "CHECK_TRACKS": True,
        "CHECK_TRACKS_SPOTIFY_PLAYLISTS": ["playlist"],
        "SPOTIFY_CLIENT_ID": "",
    }
    with pytest.raises(
        ValueError,
        match=(
            "Without all the configuration options SPOTIFY_CLIENT_ID, "
            "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI set to "
            "valid values, you cannot use CHECK_TRACKS_SPOTIFY_PLAYLISTS"
        ),
    ):
        UtilsConfig(**cfg)

"""Testing for the config module."""

import os
import re

import pytest

from djtools.utils.config import UtilsConfig


def test_utilsconfig_aws_profile_not_set():
    """Test for the UtilsConfig class."""
    cfg = {"CHECK_TRACKS": True}
    os.environ["AWS_PROFILE"] = ""  # pylint: disable=no-member
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Without AWS_PROFILE set to a valid profile ('default' or otherwise) "
            "you cannot use the CHECK_TRACKS feature"
        ),
    ):
        UtilsConfig(**cfg)


def test_utilsconfig_spotify_creds_warning(caplog):
    """Test the UtilsConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "CHECK_TRACKS": True,
        "CHECK_TRACKS_SPOTIFY_PLAYLISTS": ["playlist"],
        "AWS_PROFILE": "default",
    }
    os.environ["AWS_PROFILE"] = "default"  # pylint: disable=no-member
    UtilsConfig(**cfg)
    assert caplog.records[0].message == (
        "CHECK_TRACKS depends on valid Spotify API credentials in "
        "SpotifyConfig."
    )


def test_utilsconfig_recording_file_not_set():
    """Test for the UtilsConfig class."""
    cfg = {
        "PROCESS_RECORDING": True,
        "RECORDING_FILE": "notreal",
    }
    with pytest.raises(
        RuntimeError, match='Could not find RECORDING_FILE "notreal"'
    ):
        UtilsConfig(**cfg)


def test_utilsconfig_recording_playlist_not_set():
    """Test for the UtilsConfig class."""
    cfg = {
        "PROCESS_RECORDING": True,
        "RECORDING_FILE": "",
        "RECORDING_PLAYLIST": "",
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "You must provide a playlist name as RECORDING_PLAYLIST "
            "and this name must exists in spotify_playlists.yaml."
        ),
    ):
        UtilsConfig(**cfg)


@pytest.mark.parametrize("bit_rate", ["35", "321"])
def test_utilsconfig_validates_bitrate_error(bit_rate):
    """Test for the UtilsConfig class."""
    cfg = {"AUDIO_BITRATE": bit_rate}
    with pytest.raises(
        ValueError,
        match=re.escape("AUDIO_BITRATE must be in the range [36, 320]"),
    ):
        UtilsConfig(**cfg)


@pytest.mark.parametrize("bit_rate", ["36", "178", "320"])
def test_utilsconfig_validates_bitrate_success(bit_rate):
    """Test for the UtilsConfig class."""
    cfg = {"AUDIO_BITRATE": bit_rate}
    config = UtilsConfig(**cfg)
    assert config.AUDIO_BITRATE == str(bit_rate)


def test_utilsconfig_validate_format_warning(caplog):
    """Test for the UtilsConfig class."""
    caplog.set_level("WARNING")
    cfg = {"AUDIO_FORMAT": "mp3", "NORMALIZE_AUDIO": True}
    _ = UtilsConfig(**cfg)
    assert caplog.records[0].message == (
        "You must install FFmpeg in order to use non-wav file formats."
    )

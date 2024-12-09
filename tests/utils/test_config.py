"""Testing for the config module."""

import os
import re

import pytest

from djtools.utils.config import UtilsConfig


def test_utilsconfig_aws_profile_not_set():
    """Test for the UtilsConfig class."""
    cfg = {"check_tracks": True}
    os.environ["AWS_PROFILE"] = ""  # pylint: disable=no-member
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Without aws_profile set to a valid profile ('default' or otherwise) "
            "you cannot use the check_tracks feature"
        ),
    ):
        UtilsConfig(**cfg)


def test_utilsconfig_spotify_creds_warning(caplog):
    """Test the UtilsConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "check_tracks": True,
        "check_tracks_spotify_playlists": ["playlist"],
    }
    os.environ["AWS_PROFILE"] = "default"  # pylint: disable=no-member
    UtilsConfig(**cfg)
    assert caplog.records[0].message == (
        "check_tracks depends on valid Spotify API credentials in "
        "SpotifyConfig."
    )


def test_utilsconfig_recording_file_not_set():
    """Test for the UtilsConfig class."""
    cfg = {
        "process_recording": True,
        "recording_file": "notreal",
    }
    with pytest.raises(
        RuntimeError, match='Could not find recording_file "notreal"'
    ):
        UtilsConfig(**cfg)


def test_utilsconfig_recording_playlist_not_set():
    """Test for the UtilsConfig class."""
    cfg = {
        "process_recording": True,
        "recording_file": "",
        "recording_playlist": "",
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "You must provide a playlist name as recording_playlist "
            "and this name must exists in spotify_playlists.yaml."
        ),
    ):
        UtilsConfig(**cfg)


@pytest.mark.parametrize("bit_rate", ["35", "321"])
def test_utilsconfig_validates_bitrate_error(bit_rate):
    """Test for the UtilsConfig class."""
    cfg = {"audio_bitrate": bit_rate}
    with pytest.raises(
        ValueError,
        match=re.escape("audio_bitrate must be in the range [36, 320]"),
    ):
        UtilsConfig(**cfg)


@pytest.mark.parametrize("bit_rate", ["36", "178", "320"])
def test_utilsconfig_validates_bitrate_success(bit_rate):
    """Test for the UtilsConfig class."""
    cfg = {"audio_bitrate": bit_rate}
    config = UtilsConfig(**cfg)
    assert config.audio_bitrate == str(bit_rate)


def test_utilsconfig_validate_format_warning(caplog):
    """Test for the UtilsConfig class."""
    caplog.set_level("WARNING")
    cfg = {"audio_format": "mp3", "normalize_audio": True}
    _ = UtilsConfig(**cfg)
    assert caplog.records[0].message == (
        "You must install FFmpeg in order to use non-wav file formats."
    )

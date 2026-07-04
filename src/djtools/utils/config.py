"""This module contains the configuration object for the utils package. The
attributes of this configuration object correspond with the "utils" key of
config.yaml
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    field_validator,
    model_validator,
)

from djtools.configs.config_formatter import BaseConfigFormatter

logger = logging.getLogger(__name__)

# Audio bitrate bounds (kbps) for MP3 encoding
MIN_AUDIO_BITRATE = 36
MAX_AUDIO_BITRATE = 320


class AudioFormats(Enum):
    # pylint: disable=missing-class-docstring
    AAC = "aac"
    AIFF = "aiff"
    ALAC = "alac"
    FLAC = "flac"
    MP3 = "mp3"
    OGG = "ogg"
    PCM = "pcm"
    WAV = "wav"
    WMA = "wma"


def audio_formats_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar("!AudioFormats", data.value)


def audio_formats_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return AudioFormats(loader.construct_scalar(node))


yaml.add_representer(AudioFormats, audio_formats_representer)
yaml.add_constructor("!AudioFormats", audio_formats_constructor)


class TrimInitialSilenceMode(Enum):
    # pylint: disable=missing-class-docstring
    AUTO = "auto"
    SMART = "smart"


def trim_initial_silence_mode_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar(  # pragma: no cover
        "!TrimInitialSilenceMode", data.value
    )


def trim_initial_silence_mode_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return TrimInitialSilenceMode(  # pragma: no cover
        loader.construct_scalar(node)
    )


yaml.add_representer(
    TrimInitialSilenceMode, trim_initial_silence_mode_representer
)
yaml.add_constructor(
    "!TrimInitialSilenceMode", trim_initial_silence_mode_constructor
)


class UtilsConfig(BaseConfigFormatter):
    """Configuration object for the utils package."""

    audio_bitrate: str = "320"
    audio_destination: Optional[Path] = None
    audio_format: AudioFormats = AudioFormats.MP3
    audio_headroom: NonNegativeFloat = 0.0
    check_tracks: bool = False
    check_tracks_fuzz_ratio: NonNegativeInt = 80
    check_tracks_spotify_playlists: List[str] = Field(default_factory=list)
    local_dirs: List[Path] = Field(default_factory=list)
    normalize_audio: bool = False
    process_recording: bool = False
    recording_file: Optional[Path] = None
    recording_playlist: str = ""
    trim_initial_silence: Union[int, TrimInitialSilenceMode] = 0
    url_download: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: aws_profile must be set for check_tracks.
        """

        super().__init__(*args, **kwargs)
        if self.check_tracks:
            if not os.environ.get("AWS_PROFILE"):
                raise RuntimeError(
                    "Without aws_profile set to a valid profile ('default' or "
                    "otherwise) you cannot use the check_tracks feature"
                )
            if self.check_tracks_spotify_playlists:
                logger.warning(
                    "check_tracks depends on valid Spotify API credentials in "
                    "SpotifyConfig."
                )

        if self.process_recording:
            if not self.recording_file.exists():
                raise RuntimeError(
                    f'Could not find recording_file "{self.recording_file}"'
                )
            if not self.recording_playlist:
                raise RuntimeError(
                    "You must provide a playlist name as recording_playlist "
                    "and this name must exists in spotify_playlists.yaml."
                )

    @field_validator("audio_bitrate")
    @classmethod
    def bitrate_validation(cls, value: str) -> str:
        """Validates audio_bitrate is in the range and casts it to a string.

        Args:
            value: audio_bitrate field

        Raises:
            ValueError: audio_bitrate must be in the range [36, 320]

        Returns:
            String representing the bit rate.
        """
        value = int(value)
        if value < MIN_AUDIO_BITRATE or value > MAX_AUDIO_BITRATE:
            raise ValueError(
                f"audio_bitrate must be in the range "
                f"[{MIN_AUDIO_BITRATE}, {MAX_AUDIO_BITRATE}]"
            )

        return str(value)

    @model_validator(mode="after")
    @classmethod
    def format_validation(cls, model: "UtilsConfig") -> "UtilsConfig":
        """Logs a warning message to install FFmpeg if audio_format isn't wav.

        Args:
            model: The validated model instance.

        Returns:
            The validated model instance.
        """
        if model.audio_format != "wav" and (
            model.normalize_audio or model.process_recording
        ):
            logger.warning(
                "You must install FFmpeg in order to use non-wav file formats."
            )

        return model

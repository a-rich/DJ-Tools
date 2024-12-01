"""This module contains the configuration object for the utils package. The
attributes of this configuration object correspond with the "utils" key of
config.yaml
"""

import logging
import os
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import (
    field_validator,
    model_validator,
    NonNegativeFloat,
    NonNegativeInt,
)

from djtools.configs.config_formatter import BaseConfigFormatter


logger = logging.getLogger(__name__)


class UtilsConfig(BaseConfigFormatter):
    """Configuration object for the utils package."""

    audio_bitrate: str = "320"
    audio_destination: Optional[Path] = None
    audio_format: Literal[
        "aac", "aiff", "alac", "flac", "mp3", "ogg", "pcm", "wav", "wma"
    ] = "mp3"
    audio_headroom: NonNegativeFloat = 0.0
    check_tracks: bool = False
    check_tracks_fuzz_ratio: NonNegativeInt = 80
    check_tracks_spotify_playlists: List[str] = []
    local_dirs: List[Path] = []
    normalize_audio: bool = False
    process_recording: bool = False
    recording_file: Optional[Path] = None
    recording_playlist: str = ""
    trim_initial_silence: Union[int, Literal["auto", "smart"]] = 0
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
        if value < 36 or value > 320:
            raise ValueError("audio_bitrate must be in the range [36, 320]")

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

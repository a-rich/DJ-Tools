"""This module contains the configuration object for the utils package. The
attributes of this configuration object correspond with the "utils" key of
config.yaml
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from typing_extensions import Literal, Union

from pydantic import (
    field_validator,
    NonNegativeFloat,
    NonNegativeInt,
    root_validator,
)

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class UtilsConfig(BaseConfig):
    """Configuration object for the utils package."""

    AUDIO_BITRATE: str = "320"
    AUDIO_DESTINATION: Optional[Path] = None
    AUDIO_FORMAT: Literal[
        "aac", "aiff", "alac", "flac", "mp3", "ogg", "pcm", "wav", "wma"
    ] = "mp3"
    AUDIO_HEADROOM: NonNegativeFloat = 0.0
    CHECK_TRACKS: bool = False
    CHECK_TRACKS_FUZZ_RATIO: NonNegativeInt = 80
    CHECK_TRACKS_SPOTIFY_PLAYLISTS: List[str] = []
    LOCAL_DIRS: List[Path] = []
    NORMALIZE_AUDIO: bool = False
    PROCESS_RECORDING: bool = False
    RECORDING_FILE: Optional[Path] = None
    RECORDING_PLAYLIST: str = ""
    TRIM_INITIAL_SILENCE: Union[int, Literal["auto", "smart"]] = 0
    URL_DOWNLOAD: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            ValueError: AWS_PROFILE must be set for CHECK_TRACKS.
        """

        super().__init__(*args, **kwargs)
        if self.CHECK_TRACKS:
            if not os.environ.get("AWS_PROFILE"):
                raise RuntimeError(
                    "Without AWS_PROFILE set to a valid profile ('default' or "
                    "otherwise) you cannot use the CHECK_TRACKS feature"
                )
            if self.CHECK_TRACKS_SPOTIFY_PLAYLISTS:
                logger.warning(
                    "CHECK_TRACKS depends on valid Spotify API credentials in "
                    "SpotifyConfig."
                )

        if self.PROCESS_RECORDING:
            if not self.RECORDING_FILE.exists():
                raise RuntimeError(
                    f'Could not find RECORDING_FILE "{self.RECORDING_FILE}"'
                )
            if not self.RECORDING_PLAYLIST:
                raise RuntimeError(
                    "You must provide a playlist name as RECORDING_PLAYLIST "
                    "and this name must exists in spotify_playlists.yaml."
                )

    @field_validator("AUDIO_BITRATE")
    @classmethod
    def bitrate_validation(cls, value: str) -> str:
        """Validates AUDIO_BITRATE is in the range and casts it to a string.

        Args:
            value: AUDIO_BITRATE field

        Raises:
            ValueError: AUDIO_BITRATE must be in the range [36, 320]

        Returns:
            String representing the bit rate.
        """
        value = int(value)
        if value < 36 or value > 320:
            raise ValueError("AUDIO_BITRATE must be in the range [36, 320]")

        return str(value)

    @root_validator(skip_on_failure=True)
    @classmethod
    def format_validation(cls, values: Dict) -> str:
        """Logs a warning message to install FFmpeg if AUDIO_FORMAT isn't wav.

        Args:
            values: All model fields.

        Returns:
            Dict of all model fields.
        """
        if values["AUDIO_FORMAT"] != "wav" and (
            values["NORMALIZE_AUDIO"] or values["PROCESS_RECORDING"]
        ):
            logger.warning(
                "You must install FFmpeg in order to use non-wav file formats."
            )

        return values

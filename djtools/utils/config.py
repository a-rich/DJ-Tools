"""This module contains the configuration object for the utils package. The
attributes of this configuration object correspond with the "utils" key of
config.yaml
"""
import logging
import os
from pathlib import Path
from typing import List

from pydantic import NonNegativeInt

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class UtilsConfig(BaseConfig):
    """Configuration object for the utils package."""

    CHECK_TRACKS: bool = False
    CHECK_TRACKS_FUZZ_RATIO: NonNegativeInt = 80
    CHECK_TRACKS_LOCAL_DIRS:  List[Path] = []
    CHECK_TRACKS_SPOTIFY_PLAYLISTS:  List[str] = []
    URL_DOWNLOAD: str = ""
    URL_DOWNLOAD_DESTINATION: Path = None

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

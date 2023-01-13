import logging
from typing import List

from pydantic import NonNegativeInt

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class UtilsConfig(BaseConfig):
    """Configuration object for the utils package."""

    CHECK_TRACKS: bool = False 
    CHECK_TRACKS_FUZZ_RATIO: NonNegativeInt = 80
    CHECK_TRACKS_LOCAL_DIRS:  List[str] = []
    CHECK_TRACKS_SPOTIFY_PLAYLISTS:  List[str] = []
    URL_DOWNLOAD: str = ""
    URL_DOWNLOAD_DESTINATION: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            ValueError: AWS_PROFILE must be set for CHECK_TRACKS.
        """

        super().__init__(*args, **kwargs)
        if self.CHECK_TRACKS:
            if not self.AWS_PROFILE:
                msg = "Config must include AWS_PROFILE for CHECK_TRACKS"
                logger.critical(msg)
                raise ValueError(msg)
            logger.warning(
                "CHECK_TRACKS depends on valid Spotify API credentials in "
                "SpotifyConfig."
            )

import logging
from typing import List

from pydantic import NonNegativeInt

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class UtilsConfig(BaseConfig):

    CHECK_TRACKS: bool = False 
    CHECK_TRACKS_FUZZ_RATIO: NonNegativeInt = 80
    CHECK_TRACKS_LOCAL_DIRS:  List[str] = []
    CHECK_TRACKS_SPOTIFY_PLAYLISTS:  List[str] = []
    YOUTUBE_DL_LOCATION: str = ""
    YOUTUBE_DL_URL: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.CHECK_TRACKS:
            if not self.AWS_PROFILE:
                msg = "Config must include AWS_PROFILE for CHECK_TRACKS"
                logger.critical(msg)
                raise ValueError(msg)

            if self.CHECK_TRACKS_SPOTIFY_PLAYLISTS and not all(
                [
                    self.SPOTIFY_CLIENT_ID,
                    self.SPOTIFY_CLIENT_SECRET,
                    self.SPOTIFY_REDIRECT_URI,
                ]
            ):
                raise ValueError(
                    "Without all the configuration options SPOTIFY_CLIENT_ID, "
                    "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI set to "
                    "valid values, you cannot use CHECK_TRACKS_SPOTIFY_PLAYLISTS"
                )

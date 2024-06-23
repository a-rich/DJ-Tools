"""This module contains the configuration object for the spotify package.
The attributes of this configuration object correspond with the "spotify" key
of config.yaml
"""

import logging
from typing import List
from typing_extensions import Literal

from pydantic import BaseModel, NonNegativeInt

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class SubredditConfig(BaseModel):
    """Configuration object for SPOTIFY_PLAYLISTS."""

    name: str
    limit: NonNegativeInt = 50
    period: Literal["all", "day", "hour", "month", "week", "year"] = "week"
    type: Literal["controversial", "hot", "new", "rising", "top"] = "hot"


class SpotifyConfig(BaseConfig):
    """Configuration object for the spotify package."""

    SPOTIFY_PLAYLIST_DEFAULT_LIMIT: NonNegativeInt = 50
    SPOTIFY_PLAYLIST_DEFAULT_PERIOD: str = "week"
    SPOTIFY_PLAYLIST_DEFAULT_TYPE: str = "hot"
    SPOTIFY_PLAYLIST_FROM_UPLOAD: bool = False
    SPOTIFY_PLAYLIST_FUZZ_RATIO: NonNegativeInt = 70
    SPOTIFY_PLAYLIST_POST_LIMIT: NonNegativeInt = 100
    SPOTIFY_PLAYLIST_SUBREDDITS: List[SubredditConfig] = []
    SPOTIFY_PLAYLISTS: bool = False
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = ""
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = ""
    SPOTIFY_USERNAME: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: Spotify API credentials must exit.
            RuntimeError: Spotify API credentials must be valid.
            RuntimeError: Reddit API credentials must exist.
        """
        super().__init__(*args, **kwargs)

        if (
            self.SPOTIFY_PLAYLISTS or self.SPOTIFY_PLAYLIST_FROM_UPLOAD
        ) and not all(
            [
                self.SPOTIFY_CLIENT_ID,
                self.SPOTIFY_CLIENT_SECRET,
                self.SPOTIFY_REDIRECT_URI,
                self.SPOTIFY_USERNAME,
            ]
        ):
            raise RuntimeError(
                "Without all the configuration options SPOTIFY_CLIENT_ID, "
                "SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, and "
                "SPOTIFY_USERNAME set to valid values, you cannot use "
                "SPOTIFY_PLAYLISTS or SPOTIFY_PLAYLIST_FROM_UPLOAD"
            )
        if self.SPOTIFY_PLAYLISTS or self.SPOTIFY_PLAYLIST_FROM_UPLOAD:
            from djtools.spotify.helpers import get_spotify_client

            spotify = get_spotify_client(self)
            try:
                spotify.current_user()
            except Exception as exc:
                raise RuntimeError("Spotify credentials are invalid!") from exc

        if self.SPOTIFY_PLAYLISTS and not all(
            [
                self.REDDIT_CLIENT_ID,
                self.REDDIT_CLIENT_SECRET,
                self.REDDIT_USER_AGENT,
            ]
        ):
            raise RuntimeError(
                "Without all the configuration options REDDIT_CLIENT_ID, "
                "REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT, set to valid "
                "values, you cannot use SPOTIFY_PLAYLISTS"
            )

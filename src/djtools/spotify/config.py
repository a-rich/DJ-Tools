"""This module contains the configuration object for the spotify package.
The attributes of this configuration object correspond with the "spotify" key
of config.yaml
"""

import logging
from typing import List, Literal

from pydantic import BaseModel, NonNegativeInt

from djtools.configs.config_formatter import BaseConfigFormatter


logger = logging.getLogger(__name__)


class SubredditConfig(BaseModel):
    """Configuration object for spotify_playlists."""

    name: str
    limit: NonNegativeInt = 50
    period: Literal["all", "day", "hour", "month", "week", "year"] = "week"
    type: Literal["controversial", "hot", "new", "rising", "top"] = "hot"


class SpotifyConfig(BaseConfigFormatter):
    """Configuration object for the spotify package."""

    spotify_playlist_default_limit: NonNegativeInt = 50
    spotify_playlist_default_period: str = "week"
    spotify_playlist_default_type: str = "hot"
    spotify_playlist_from_upload: bool = False
    spotify_playlist_fuzz_ratio: NonNegativeInt = 70
    spotify_playlist_post_limit: NonNegativeInt = 100
    spotify_playlist_subreddits: List[SubredditConfig] = []
    spotify_playlists: bool = False
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = ""
    spotify_username: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: Spotify API credentials must exit.
            RuntimeError: Spotify API credentials must be valid.
            RuntimeError: Reddit API credentials must exist.
        """
        super().__init__(*args, **kwargs)

        if (
            self.spotify_playlists or self.spotify_playlist_from_upload
        ) and not all(
            [
                self.spotify_client_id,
                self.spotify_client_secret,
                self.spotify_redirect_uri,
                self.spotify_username,
            ]
        ):
            raise RuntimeError(
                "Without all the configuration options spotify_client_id, "
                "spotify_client_secret, spotify_redirect_uri, and "
                "spotify_username set to valid values, you cannot use "
                "spotify_playlists or spotify_playlist_from_upload"
            )
        if self.spotify_playlists or self.spotify_playlist_from_upload:
            from djtools.spotify.helpers import get_spotify_client

            spotify = get_spotify_client(self)
            try:
                spotify.current_user()
            except Exception as exc:
                raise RuntimeError("Spotify credentials are invalid!") from exc

        if self.spotify_playlists and not all(
            [
                self.reddit_client_id,
                self.reddit_client_secret,
                self.reddit_user_agent,
            ]
        ):
            raise RuntimeError(
                "Without all the configuration options reddit_client_id, "
                "reddit_client_secret, and reddit_user_agent, set to valid "
                "values, you cannot use spotify_playlists"
            )

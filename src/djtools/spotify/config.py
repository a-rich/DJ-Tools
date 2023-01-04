"""This module contains the configuration object for the spotify package.
The attributes of this configuration object correspond with the "spotify" key
of config.yaml
"""
from enum import Enum
import logging
from typing import Dict, List, Union

from pydantic import NonNegativeInt

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class SubredditTypeEnum(Enum):
    controversial = "controversial"
    hot = "hot"
    new = "new"
    rising = "rising"
    top = "top"


class SubredditPeriodEnum(Enum):
    all = "all"
    day = "day"
    hour = "hour"
    month = "month"
    week ="week"
    year = "year"


class SpotifyConfig(BaseConfig):
    """Configuration object for the spotify package."""

    AUTO_PLAYLIST_DEFAULT_LIMIT: NonNegativeInt = 50
    AUTO_PLAYLIST_DEFAULT_PERIOD: str = "week"
    AUTO_PLAYLIST_DEFAULT_TYPE: str = "hot"
    AUTO_PLAYLIST_FUZZ_RATIO: NonNegativeInt = 70
    AUTO_PLAYLIST_POST_LIMIT: NonNegativeInt = 100
    # AUTO_PLAYLIST_SUBREDDITS: List[Dict[str, Union[NonNegativeInt, str]]] = []
    AUTO_PLAYLIST_SUBREDDITS: List[Dict[str, Union[int, str]]] = []
    AUTO_PLAYLIST_UPDATE: bool = False 
    PLAYLIST_FROM_UPLOAD: bool = False 
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = ""
    SPOTIFY_USERNAME: str  = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: Spotify API credentials must exit.
            RuntimeError: Reddit API credentials must exist.
            ValueError: Subreddit config must have a string name.
            ValueError: Subreddit config must have a valid period.
            ValueError: Subreddit config must have a valid type.
            ValueError: Subreddit config must have a non-negative limit.
        """
        super().__init__(*args, **kwargs)

        if (
            (self.AUTO_PLAYLIST_UPDATE or self.PLAYLIST_FROM_UPLOAD) and
            not all(
                [
                    self.SPOTIFY_CLIENT_ID,
                    self.SPOTIFY_CLIENT_SECRET,
                    self.SPOTIFY_REDIRECT_URI,
                    self.SPOTIFY_USERNAME
                ]
            )
        ):
            raise RuntimeError(
                "Without all the configuration options SPOTIFY_CLIENT_ID, "
                "SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, and "
                "SPOTIFY_USERNAME set to valid values, you cannot use "
                "AUTO_PLAYLIST_UPDATE or PLAYLIST_FROM_UPLOAD"
            )
        
        if self.AUTO_PLAYLIST_UPDATE and not all(
            [
                self.REDDIT_CLIENT_ID,
                self.REDDIT_CLIENT_SECRET,
                self.REDDIT_USER_AGENT,
            ]
        ):
            raise RuntimeError(
                "Without all the configuration options REDDIT_CLIENT_ID, "
                "REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT, set to valid "
                "values, you cannot use AUTO_PLAYLIST_UPDATE"
            )

        # Validate Subreddit configuration objects.
        for cfg in self.AUTO_PLAYLIST_SUBREDDITS:
            if not isinstance(cfg.get("name"), str):
                raise ValueError("Subreddit name must be a string")
            if (
                cfg.get("type", self.AUTO_PLAYLIST_DEFAULT_TYPE)
                not in SubredditTypeEnum.__members__
            ):
                raise ValueError(
                    f"Subreddit type={cfg['type']} is invalid...accepted "
                    "values are "
                    f"{list(map(str, SubredditTypeEnum.__members__))}"
                )
            if (
                cfg.get("period", self.AUTO_PLAYLIST_DEFAULT_PERIOD)
                not in SubredditPeriodEnum.__members__
            ):
                raise ValueError(
                    f"Subreddit period={cfg['period']} is invalid...accepted "
                    "values are "
                    f"{list(map(str, SubredditPeriodEnum.__members__))}"
                )
            if (
                cfg.get("limit", self.AUTO_PLAYLIST_DEFAULT_LIMIT) < 0
            ):
                raise ValueError("Subreddit limit must be non-negative")

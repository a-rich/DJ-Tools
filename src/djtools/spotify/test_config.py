import re
from unittest import mock

import pytest

from djtools.spotify.config import (
    SpotifyConfig, SubredditPeriodEnum, SubredditTypeEnum
)


def test_spotifyconfig():
    SpotifyConfig()


def test_spotifyconfig_no_spotify_credentials():
    cfg = {"PLAYLIST_FROM_UPLOAD": True, "SPOTIFY_CLIENT_ID": ""}
    with pytest.raises(
        RuntimeError,
        match=(
            "Without all the configuration options SPOTIFY_CLIENT_ID, "
            "SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, and "
            "SPOTIFY_USERNAME set to valid values, you cannot use "
            "AUTO_PLAYLIST_UPDATE or PLAYLIST_FROM_UPLOAD"
        ),
    ):
        SpotifyConfig(**cfg)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig_no_reddit_credentials(mock_get_spotify_client):
    cfg = {
        "AUTO_PLAYLIST_UPDATE": True,
        "REDDIT_CLIENT_ID": "",
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Without all the configuration options REDDIT_CLIENT_ID, "
            "REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT, set to valid "
            "values, you cannot use AUTO_PLAYLIST_UPDATE"
        ),
    ):
        SpotifyConfig(**cfg)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig_subreddit_config_bad_limit(mock_get_spotify_client):
    cfg = {
        "AUTO_PLAYLIST_UPDATE": True,
        "AUTO_PLAYLIST_SUBREDDITS": [{"name": "subredd", "limit": -1}],
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
        "REDDIT_CLIENT_ID": "id",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USER_AGENT": "user ageng",
    }
    with pytest.raises(
        ValueError, match="Subreddit limit must be non-negative"
    ):
        SpotifyConfig(**cfg)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig_subreddit_config_bad_name(mock_get_spotify_client):
    cfg = {
        "AUTO_PLAYLIST_UPDATE": True,
        "AUTO_PLAYLIST_SUBREDDITS": [{"name": 4}],
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
        "REDDIT_CLIENT_ID": "id",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USER_AGENT": "user ageng",
    }
    with pytest.raises(
        ValueError, match="Subreddit name must be a string"
    ):
        SpotifyConfig(**cfg)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig_subreddit_config_bad_period(mock_get_spotify_client):
    cfg = {
        "name": "subreddit",
        "period": "not a real period",
    }
    full_cfg = {
        "AUTO_PLAYLIST_UPDATE": True,
        "AUTO_PLAYLIST_SUBREDDITS": [cfg],
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
        "REDDIT_CLIENT_ID": "id",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USER_AGENT": "user ageng",
    }
    with pytest.raises(
        ValueError,
        match=(
            re.escape(f"Subreddit period={cfg['period']} is invalid...accepted ") +
            re.escape(f"values are {list(map(str, SubredditPeriodEnum.__members__))}")
        )
    ):
        SpotifyConfig(**full_cfg)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig_subreddit_config_bad_type(mock_get_spotify_client):
    cfg = {
        "name": "subreddit",
        "type": "not a real type",
    }
    full_cfg = {
        "AUTO_PLAYLIST_UPDATE": True,
        "AUTO_PLAYLIST_SUBREDDITS": [cfg],
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
        "REDDIT_CLIENT_ID": "id",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USER_AGENT": "user ageng",
    }
    with pytest.raises(
        ValueError,
        match=(
            re.escape(f"Subreddit type={cfg['type']} is invalid...accepted ") +
            re.escape(f"values are {list(map(str, SubredditTypeEnum.__members__))}")
        )
    ):
        SpotifyConfig(**full_cfg)

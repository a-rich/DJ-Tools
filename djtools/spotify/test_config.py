from unittest import mock

import pytest

from djtools.spotify.config import SpotifyConfig


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_spotifyconfig(mock_get_spotify_client):
    SpotifyConfig()


@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_baseconfig_invalid_spotify_credentials(mock_spotify):
    mock_spotify.return_value.current_user.side_effect = Exception()
    cfg = {
        "PLAYLIST_FROM_UPLOAD": True,
        "SPOTIFY_CLIENT_ID": "not a real ID",
        "SPOTIFY_CLIENT_SECRET": "not a real secret",
        "SPOTIFY_REDIRECT_URI": "not a real URI",
        "SPOTIFY_USERNAME": "not a real username",
    }
    with pytest.raises(RuntimeError, match="Spotify credentials are invalid!"):
        SpotifyConfig(**cfg)


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
        
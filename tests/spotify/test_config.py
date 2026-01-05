"""Testing for the config module."""

from unittest import mock

import pytest

from djtools.spotify.config import SpotifyConfig


@mock.patch("djtools.spotify.helpers.Client")
def test_baseconfig_invalid_spotify_credentials(mock_client):
    """Test for the SpotifyConfig class with invalid credentials."""
    mock_client.return_value.current_user.side_effect = Exception()
    cfg = {
        "spotify_client_id": "not a real ID",
        "spotify_client_secret": "not a real secret",
        "spotify_playlist_from_upload": True,
        "spotify_redirect_uri": "not a real URI",
        "spotify_username": "not a real username",
    }
    with pytest.raises(RuntimeError, match="Spotify credentials are invalid!"):
        SpotifyConfig(**cfg)


def test_spotifyconfig_no_spotify_credentials():
    """Test for the SpotifyConfig class without credentials."""
    cfg = {"spotify_playlist_from_upload": True, "spotify_client_id": ""}
    with pytest.raises(
        RuntimeError,
        match=(
            "Without all the configuration options spotify_client_id, "
            "spotify_client_secret, spotify_redirect_uri, and "
            "spotify_username set to valid values, you cannot use "
            "spotify_playlists or spotify_playlist_from_upload"
        ),
    ):
        SpotifyConfig(**cfg)


@mock.patch("djtools.spotify.helpers.Client")
def test_spotifyconfig_no_reddit_credentials(_mock_client):
    """Test for the SpotifyConfig class without Reddit credentials."""
    cfg = {
        "reddit_client_id": "",
        "spotify_client_id": "id",
        "spotify_client_secret": "secret",
        "spotify_playlists": True,
        "spotify_redirect_uri": "uri",
        "spotify_username": "name",
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Without all the configuration options reddit_client_id, "
            "reddit_client_secret, and reddit_user_agent, set to valid "
            "values, you cannot use spotify_playlists"
        ),
    ):
        SpotifyConfig(**cfg)

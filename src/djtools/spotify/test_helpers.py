from unittest import mock

import pytest

from djtools.spotify.helpers import get_playlist_ids, get_spotify_client


@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
def test_get_spotify_client(test_config):
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    get_spotify_client(test_config)


def test_get_spotify_clientmissing_spotify_configs(test_config):
    del test_config["SPOTIFY_CLIENT_ID"]
    with pytest.raises(
        KeyError,
        match="Using the spotify package requires the following config "
            "options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
    ):
        get_spotify_client(test_config)
        

def test_get_spotify_client_bad_spotify_configs(test_config):
    with pytest.raises(
        Exception,
        match="Failed to instantiate the Spotify client",
    ):
        get_spotify_client(test_config)


def test_get_playlist_ids():
    playlist_ids = get_playlist_ids()
    assert isinstance(playlist_ids, dict)

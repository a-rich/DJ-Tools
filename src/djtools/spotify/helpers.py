"""This module contains helper functions used by the "spotify" module. Helper
functions include getting a Spotipy API client and loading configuration files
with Spotify playlist names and IDs."""
import json
import os
from typing import Dict, List, Union

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def get_spotify_client(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
) -> spotipy.Spotify:
    """Instantiate a Spotify API client.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", and
            "SPOTIFY_REDIRECT_URI" must be configured.
        Exception: Spotify client must be instantiated.

    Returns:
        Spotify API client.
    """
    try:
        spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["SPOTIFY_CLIENT_ID"],
                client_secret=config["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=config["SPOTIFY_REDIRECT_URI"],
                scope="playlist-modify-public",
                requests_timeout=30,
                cache_handler=spotipy.CacheFileHandler(
                    cache_path=os.path.join(
                        os.path.dirname(__file__), ".spotify.cache"
                    ).replace(os.sep, "/"),
                ),
            )
        )
    except KeyError:
        raise KeyError(
            "Using the spotify package requires the following config options: "
            "SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI"
        ) from KeyError 
    except Exception as exc:
        raise Exception(f"Failed to instantiate the Spotify client: {exc}")
    
    return spotify


def get_playlist_ids() -> Dict[str, str]:
    """Load Spotify playlist names -> IDs lookup.

    Returns:
        Dictionary of Spotify playlist names mapped to playlist IDs. 
    """
    playlist_ids = {}
    ids_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "playlists.json",
    ).replace(os.sep, "/")
    if os.path.exists(ids_path):
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            playlist_ids = json.load(_file)
    
    return playlist_ids

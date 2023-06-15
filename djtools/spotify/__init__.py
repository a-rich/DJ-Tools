"""The `spotify` package contains modules:
    * `config`: the configuration object for the `spotify` package
    * `helpers`: helper functions for `playlist_builder`
    * `playlist_builder`: constructs or updates Spotify playlists using either
        Subreddit posts or the Discord webhook output from `UPLOAD_MUSIC`
"""
from djtools.spotify.config import SpotifyConfig
from djtools.spotify.playlist_builder import (
    spotify_playlist_from_upload, spotify_playlists
)


SPOTIFY_OPERATIONS = {
    "SPOTIFY_PLAYLIST_FROM_UPLOAD": spotify_playlist_from_upload,
    "SPOTIFY_PLAYLISTS": spotify_playlists,
}


__all__ = (
    "spotify_playlist_from_upload",
    "SpotifyConfig",
    "SPOTIFY_OPERATIONS",
    "spotify_playlists",
)

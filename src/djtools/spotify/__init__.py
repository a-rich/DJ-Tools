"""The `spotify` package contains modules:
    * `config`: the configuration object for the `spotify` package
    * `helpers`: helper functions for `playlist_builder`
    * `playlist_builder`: constructs or updates Spotify playlists using either
        Subreddit posts or the Discord webhook output from `UPLOAD_MUSIC`
"""
from djtools.spotify.config import SpotifyConfig
from djtools.spotify.playlist_builder import (
    playlist_from_upload, update_auto_playlists
)


SPOTIFY_OPERATIONS = {
    "PLAYLIST_FROM_UPLOAD": playlist_from_upload,
    "AUTO_PLAYLIST_UPDATE": update_auto_playlists,
}


__all__ = (
    "playlist_from_upload",
    "SpotifyConfig",
    "SPOTIFY_OPERATIONS",
    "update_auto_playlists",
)

"""The "spotify" package contains a module for constructing / updating Spotify
playlists from subreddit posts and / or the Discord webhook output from music
uploads.
"""
from djtools.spotify.playlist_builder import (
    playlist_from_upload, update_auto_playlists
)


SPOTIFY_OPERATIONS = {
    "PLAYLIST_FROM_UPLOAD": playlist_from_upload,
    "AUTO_PLAYLIST_UPDATE": update_auto_playlists,
}


__all__ = (
    "playlist_from_upload",
    "SPOTIFY_OPERATIONS",
    "update_auto_playlists",
)

"""The "spotify" package contains a module for checking Spotify playlists for
tracks that overlap with those already in the beatcloud. It also contains a
module for constructing / updating Spotify playlists from subreddit top posts.
"""
from .spotify_playlist_builder import update_auto_playlists
from .spotify_playlist_checker import check_playlists


SPOTIFY_OPERATIONS = {
    "CHECK_TRACK_OVERLAP": check_playlists,
    "AUTO_PLAYLIST_UPDATE": update_auto_playlists,
}


__all__ = "check_playlists", "SPOTIFY_OPERATIONS", "update_auto_playlists"

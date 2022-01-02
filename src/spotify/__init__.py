"""The 'spotify' package contains a module for checking Spotify playlists for
tracks that overlap with those already in the beatcloud. It also contains a
module for constructing / updating Spotify playlists from subreddit top posts.
"""
from src.spotify.playlist_builder import update_auto_playlists
from src.spotify.playlist_checker import check_playlists


SPOTIFY_OPERATIONS = {
    "SPOTIFY_CHECK_PLAYLISTS": check_playlists,
    "AUTO_PLAYLIST_UPDATE": update_auto_playlists
}

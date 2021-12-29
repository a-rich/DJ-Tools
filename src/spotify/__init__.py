from src.spotify.playlist_checker import check_playlists
from src.spotify.playlist_builder import update_auto_playlists


SPOTIFY_OPERATIONS = {
    "CHECK_PLAYLISTS": check_playlists,
    "UPDATE_AUTO_PLAYLISTS": update_auto_playlists 
}

"""The "utils" package contains modules for a variety of different tasks.
    * generate_genre_playlists.py: Automatically create a desired playlist
        structure based on the genre ID3 tags present in an XML.
    * get_genres.py: Display track counts for all genres using the ID3 tag
        field of local mp3 files.
    * local_dirs_checker.py: Check local tracks for overlap with those already
        in the beatcloud.
    * randomize_tracks.py: Set ID3 tags of tracks in playlists sequentially
        (after shuffling) to randomize.
    * youtube_dl.py: Download tracks from a URL (e.g. Soundcloud playlist).
"""
from djtools.utils.generate_genre_playlists import generate_genre_playlists
from djtools.utils.get_genres import get_genres
from djtools.utils.local_dirs_checker import check_local_dirs
from djtools.utils.randomize_tracks import randomize_tracks
from djtools.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    "GENERATE_GENRE_PLAYLISTS": generate_genre_playlists,
    "GET_GENRES": get_genres,
    "CHECK_TRACK_OVERLAP": check_local_dirs,
    "RANDOMIZE_TRACKS": randomize_tracks,
    "YOUTUBE_DL": youtube_dl,
}

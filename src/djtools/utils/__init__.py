"""The "utils" package contains modules for a variety of different tasks.
    * generate_tags_playlists.py: Automatically create a desired playlist
        structure based on the tags present in an XML.
    * local_dirs_checker.py: Check local tracks for overlap with those already
        in the beatcloud.
    * randomize_tracks.py: Set ID3 tags of tracks in playlists sequentially
        (after shuffling) to randomize.
    * youtube_dl.py: Download tracks from a URL (e.g. Soundcloud playlist).
"""
from djtools.utils.generate_tags_playlists import generate_tags_playlists
from djtools.utils.local_dirs_checker import check_local_dirs
from djtools.utils.randomize_tracks import randomize_tracks
from djtools.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    "GENERATE_TAGS_PLAYLISTS": generate_tags_playlists,
    "CHECK_TRACK_OVERLAP": check_local_dirs,
    "RANDOMIZE_TRACKS": randomize_tracks,
    "YOUTUBE_DL": youtube_dl,
}

"""The 'utils' package contains modules for a variety of different tasks.
    * generate_genre_playlists.py: automatically create a desired playlist
            structure based on the genre ID3 tags present in an XML
    * get_genres.py: display track counts for all genres using the ID3 tag
            field of local mp3 files
    * randomize_tracks.py: set ID3 tags of tracks in playlists sequentially
            (after shuffling) to randomize
    * youtube_dl.py: download tracks from a URL (e.g. Soundcloud playlist)
"""
from djtools.utils.generate_genre_playlists import generate_genre_playlists
from djtools.utils.get_genres import get_genres
from djtools.utils.randomize_tracks import randomize_tracks
from djtools.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    'GENERATE_GENRE_PLAYLISTS': generate_genre_playlists,
    'GET_GENRES': get_genres,
    'RANDOMIZE_TRACKS': randomize_tracks,
    'YOUTUBE_DL': youtube_dl
}

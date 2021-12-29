from src.utils.generate_genre_playlists import generate_genre_playlists
from src.utils.get_genres import get_genres
from src.utils.randomize_tracks import randomize_tracks
from src.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    'GENERATE_GENRE_PLAYLISTS': generate_genre_playlists,
    'GET_GENRES': get_genres,
    'RANDOMIZE_TRACKS': randomize_tracks,
    'YOUTUBE_DL': youtube_dl
}

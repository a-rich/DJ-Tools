"""This module contains helper functions used by the "spotify" module. Helper
functions include getting a Spotipy API client and loading configuration files
with Spotify playlist names and IDs."""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import json
import logging
import os
from typing import Any, Dict, List, Set, Tuple, Union

from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


logger = logging.getLogger(__name__)


def get_spotify_client(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
) -> spotipy.Spotify:
    """Instantiate a Spotify API client.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", and
            "SPOTIFY_REDIRECT_URI" must be configured.
        Exception: Spotify client must be instantiated.

    Returns:
        Spotify API client.
    """
    try:
        spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["SPOTIFY_CLIENT_ID"],
                client_secret=config["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=config["SPOTIFY_REDIRECT_URI"],
                scope="playlist-modify-public",
                requests_timeout=30,
                cache_handler=spotipy.CacheFileHandler(
                    cache_path=os.path.join(
                        os.path.dirname(__file__), ".spotify.cache"
                    ).replace(os.sep, "/"),
                ),
            )
        )
    except KeyError:
        raise KeyError(
            "Using the spotify package requires the following config options: "
            "SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI"
        ) from KeyError 
    except Exception as exc:
        raise Exception(f"Failed to instantiate the Spotify client: {exc}")
    
    return spotify


def get_playlist_ids() -> Dict[str, str]:
    """Load Spotify playlist names -> IDs lookup.

    Returns:
        Dictionary of Spotify playlist names mapped to playlist IDs. 
    """
    playlist_ids = {}
    ids_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "spotify_playlists.json",
    ).replace(os.sep, "/")
    if os.path.exists(ids_path):
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            playlist_ids = json.load(_file)
    
    return playlist_ids


def get_spotify_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
) -> Dict[str, Set[str]]:
    """Aggregates the tracks from one or more Spotify playlists into a
        dictionary mapped with playlist names.

    Args:
        config: Configuration object.
    
    Returns:
        Spotify track titles and artist names keyed by playlist name.
    """
    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()
    playlist_tracks = {}
    for playlist in config.get("SPOTIFY_CHECK_PLAYLISTS", []):
        playlist_id = playlist_ids.get(playlist)
        if not playlist_id:
            logger.error(f"{playlist} not in spotify_playlists.json")
            continue

        logger.info(f'Getting tracks from Spotify playlist "{playlist}"...')
        playlist_tracks[playlist] = get_playlist_tracks(spotify, playlist_id)
        length = len(playlist_tracks[playlist])
        logger.info(f"Got {length} track{'' if length == 1 else 's'}")

        if config.get("VERBOSITY", 0) > 0:
            for track in playlist_tracks[playlist]:
                logger.info(f"\t{track}")

    return playlist_tracks


def get_playlist_tracks(
    spotify: spotipy.Spotify, playlist_id: str
) -> Set[str]:
    """Queries Spotify API for a playlist and pulls tracks from it.

    Args:
        spotify: Spotify client.
        playlist_id: Playlist ID of Spotify playlist to pull tracks from.

    Raises:
        Exception: Playlist_id must correspond with a valid Spotify playlist.

    Returns:
        Spotify track titles and artist names from a given playlist.
    """
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception:
        raise Exception(
            f"Failed to get playlist with ID {playlist_id}"
        ) from Exception

    result = playlist["tracks"]
    tracks = add_tracks(result)

    while result["next"]:
        result = spotify.next(result)
        tracks.extend(add_tracks(result))

    return set(tracks)


def add_tracks(result: Dict[str, Any]) -> List[str]:
    """Parses a page of Spotify API result tracks and returns a list of the
        track titles and artist names.

    Args:
        result: Paged result of Spotify tracks.

    Returns:
        Spotify track titles and artist names.
    """
    tracks = []
    for track in result["items"]:
        title = track["track"]["name"]
        artists = ", ".join([y["name"] for y in track["track"]["artists"]])
        tracks.append(f"{title} - {artists}")

    return tracks


def find_matches(
    spotify_tracks: Dict[str, Set[str]],
    beatcloud_tracks: List[str],
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
) -> List[Tuple[str, float]]:
    """Computes the Levenshtein similarity between the product of all beatcloud
        tracks with all the tracks in the given Spotify playlist(s) and returns
        those that match above a threshold.

    Args:
        spotify_tracks: Spotify track titles and artist names.
        beatcloud_tracks: Beatcloud track titles and artist names.
        config: Configuration object.

    Returns:
        List of tuples of Spotify playlist, Spotify track, Beatcloud track, andl
            Levenshtein distance.
    """
    spotify_tracks = [
        (playlist, track) for playlist, tracks in spotify_tracks.items()
        for track in tracks
    ]
    _product = list(product(spotify_tracks, beatcloud_tracks))
    _temp, beatcloud_tracks = zip(*_product)
    spotify_playlists, spotify_tracks = zip(*_temp)
    fuzz_ratio = config.get("CHECK_TRACK_OVERLAP_FUZZ_RATIO", 80)
    payload = [
        spotify_playlists,
        spotify_tracks,
        beatcloud_tracks,
        [fuzz_ratio] * len(_product),
    ]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        matches = list(
            filter(
                None,
                tqdm(
                    executor.map(compute_distance, *payload),
                    total=len(_product),
                    desc="Matching new and Beatcloud tracks",
                )
            )
        )

    return matches


def compute_distance(
    spotify_playlist: str,
    spotify_track: str,
    beatcloud_track: str,
    threshold: float,
) -> Tuple[str, float]:
    """Qualifies a match between a Spotify track and a beatcloud track using
        Levenshtein similarity.

    Args:
        spotify_playlist: Playlist that Spotify track belongs to.
        spotify_track: Spotify track title and artist name.
        beatcloud_track: Beatcloud track title and artist name
        threshold: Levenshtein similarity threshold for acceptance.

    Returns:
        Tuple of Spotify playlist, Spotify "TRACK TITLE - ARTIST NAME",
            beatcloud "TRACK TITLE - ARTIST NAME", Levenshtein similarity.
    """
    fuzz_ratio = fuzz.ratio(spotify_track, beatcloud_track)
    if fuzz_ratio >= threshold:
        return spotify_playlist, spotify_track, beatcloud_track, fuzz_ratio

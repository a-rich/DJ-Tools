"""This module is responsible for identifying any potential overlap between
tracks in one or more Spotify playlists with all the tracks already in the
beatcloud.
"""
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby, product
import json
import logging
from operator import itemgetter
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


logger = logging.getLogger(__name__)


def check_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
    beatcloud_tracks: List[str] = [],
) -> Optional[List[str]]:
    """Gets track titles and artists from both Spotify playlist(s) and
        beatcloud and computes the Levenshtein similarity between their product
        in order to identify any overlapping tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: List of track artist - titles from S3.

    Returns:
        List of track artist - titles from S3.
    """
    spotify_tracks = get_spotify_tracks(config)
    if not spotify_tracks:
        logger.warn(
            "There are no Spotify tracks; make sure SPOTIFY_CHECK_PLAYLISTS "
            "has one or more keys from playlist_checker.json"
        )
        return
    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks()
    matches = find_matches(spotify_tracks, beatcloud_tracks, config)
    logger.info(f"Spotify playlist(s) / beatcloud matches: {len(matches)}")
    for playlist, matches in groupby(
        sorted(matches, key=itemgetter(0)), key=itemgetter(0)
    ):
        logger.info(f"{playlist}:")
        for _, spotify_track, beatcloud_track, fuzz_ratio in matches:
            logger.info(f"\t{fuzz_ratio}: {spotify_track} | {beatcloud_track}")
    
    return beatcloud_tracks


def get_spotify_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
) -> Dict[str, Set[str]]:
    """Aggregates the tracks from one or more Spotify playlists into a
        dictionary mapped with playlist names.

    Args:
        config: Configuration object.
    
    Raises:
        KeyError: "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", and
            "SPOTIFY_REDIRECT_URI" must be configured.

    Returns:
        Spotify track titles and artist names keyed by playlist name.
    """
    try:
        spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["SPOTIFY_CLIENT_ID"],
                client_secret=config["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=config["SPOTIFY_REDIRECT_URI"],
                scope="playlist-modify-public",
                cache_path=os.path.join(
                    os.path.dirname(__file__), ".spotify.cache"
                ).replace(os.sep, "/")
            )
        )
    except KeyError:
        raise KeyError(
            "Using the playlist_checker module requires the following config "
            "options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
        ) from KeyError 

    playlist_ids_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "playlist_checker.json",
    ).replace(os.sep, "/")
    with open(playlist_ids_path, encoding="utf-8") as _file:
        playlist_ids = {
            key.lower(): value for key, value in json.load(_file).items()
        }
    playlist_tracks = {}
    for playlist in config.get("SPOTIFY_CHECK_PLAYLISTS", []):
        playlist_id = playlist_ids.get(playlist.lower())
        if not playlist_id:
            logger.error(f"{playlist} not in playlist_checker.json")
            continue

        logger.info(f'Getting tracks from Spotify playlist "{playlist}"...')
        playlist_tracks[playlist] = get_playlist_tracks(spotify, playlist_id)
        logger.info(f"Got {len(playlist_tracks[playlist])} tracks")

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


def get_beatcloud_tracks() -> List[str]:
    """Lists all the music files in S3 and parses out the track titles and
        artist names.

    Returns:
        Beatcloud track titles and artist names.
    """
    logger.info("Getting tracks from the beatcloud...")
    cmd = "aws s3 ls --recursive s3://dj.beatcloud.com/dj/music/"
    with os.popen(cmd) as proc:
        output = proc.read().split("\n")
    tracks = [
        os.path.splitext(os.path.basename(track))[0]
        for track in output if track
    ]
    logger.info(f"Got {len(tracks)} tracks")

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

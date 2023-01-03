"""This module contains helper functions that are not specific to any
particular subpackage of this library.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from glob import glob
from itertools import product
import logging
import os
from os import name as os_name
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from fuzzywuzzy import fuzz
import spotipy
from tqdm import tqdm

from djtools.spotify.helpers import get_playlist_ids, get_spotify_client


logger = logging.getLogger(__name__)


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
    tracks = [track for track in output if track]
    logger.info(f"Got {len(tracks)} tracks")

    return tracks


def get_local_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
) -> Dict[str, List[str]]:
    """Aggregates the files from one or more local directories in a dictionary
        mapped with parent directories.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "LOCAL_CHECK_DIRS" must be configured.
        ValueError: "LOCAL_CHECK_DIRS" must be configured.

    Returns:
        Local file names keyed by parent directory.
    """
    if "LOCAL_CHECK_DIRS" not in config:
        raise KeyError(
            "Using the local_dirs_checker module requires the config option "
            "LOCAL_CHECK_DIRS to be set to a list of one or more directories "
            "containing new tracks"
        )
    if not config["LOCAL_CHECK_DIRS"]:
        raise ValueError(
            "Using the local_dirs_checker module requires the config option "
            "LOCAL_CHECK_DIRS to be set to a list of one or more directories "
            "containing new tracks"
        )

    local_dir_tracks = {}
    for _dir in config["LOCAL_CHECK_DIRS"]:
        path = _dir.replace(os.sep, "/")
        if not os.path.exists(path):
            logger.warning(
                f"{path} does not exist; will not be able to check its "
                "contents against the beatcloud"
            )
            continue
        files = glob(
            os.path.join(path, "**", "*.*").replace(os.sep, "/"),
            recursive=True,
        )
        if files:
            local_dir_tracks[_dir] = [
                os.path.splitext(os.path.basename(x))[0] for x in files
            ]

    return local_dir_tracks


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


def upload_log(
    config: Dict[str, Union[List, Dict, str, bool, int, float]], log_file: str
):
    """This function uploads "log_file" to the "USER" logs folder in S3. It
        then deletes all files created more than one day ago.

    Args:
        config: Configuration object.
        log_file: Path to log file.
    """
    if not config.get("AWS_PROFILE"):
        logger.warning(
            "Logs cannot be backed up without specifying the config option "
            "AWS_PROFILE"
        )
        return

    dst = (
        "s3://dj.beatcloud.com/dj/logs/"
        f'{config["USER"]}/{os.path.basename(log_file)}'
    )
    cmd = f"aws s3 cp {log_file} {dst}"
    logger.info(cmd)
    os.system(cmd)

    now = datetime.now()
    one_day = timedelta(days=1)
    for _file in glob(f"{os.path.dirname(log_file)}/*"):
        if os.path.basename(_file) == "empty.txt":
            continue
        if os.path.getmtime(_file) < (now - one_day).timestamp():
            os.remove(_file)


def make_dirs(path: str):
    """This function performs operating system agnostic directory creation.

    Args:
        path: Directory path.
    """
    if os_name == "nt":
        cwd = os.getcwd()
        path_parts = path.split(os.sep)
        if path_parts and not path_parts[0]:
            path_parts[0] = "/"
        root = path_parts[0]
        path_parts = path_parts[1:]
        os.chdir(root)
        for part in path_parts:
            os.makedirs(part, exist_ok=True)
            os.chdir(part)
        os.chdir(cwd)
    else:
        os.makedirs(path, exist_ok=True)


def catch(
    func: Callable,
    *args,
    handle: Optional[Callable] = lambda e: None,
    **kwargs,
):  
    """This function permits one-line try/except logic for comprehensions.

    Args:
        func: Function to try.
        handle: Handler function.

    Returns:
        Callable to handle exception.
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        return handle(exc)


def raise_(exc: Exception):
    """This function permits raising exceptions in unnamed functions.

    Args:
        exc: Arbitrary exception.

    Raises:
        Arbitrary exception.
    """
    raise exc

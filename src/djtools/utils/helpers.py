"""This module contains top-level helper functions.
    * upload_logs: Writes a log file to the logs directory of S3.
"""
from datetime import datetime, timedelta
from glob import glob
from itertools import groupby
import logging
from operator import itemgetter
import os
from os import name as os_name
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from djtools.spotify.helpers import find_matches, get_spotify_tracks

logger = logging.getLogger(__name__)


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


def compare_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
    beatcloud_tracks: Optional[List[str]] = [],
) -> Tuple[List[str], List[str]]:
    """Compares tracks from Spotify / local with Beatcloud tracks.
    
    Gets track titles and artists from Spotify playlist(s) and / or file names
    from local directories, and get file names from the beatcloud. Then compute
    the Levenshtein similarity between their product in order to identify any
    overlapping tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: Cached list of tracks from S3.

    Returns:
        List of all tracks and list of full paths to matching Beatcloud tracks.
    """
    track_sets = []
    beatcloud_matches = []
    if config.get("SPOTIFY_CHECK_PLAYLISTS"):
        tracks = get_spotify_tracks(config)
        if not tracks:
            logger.warning(
                "There are no Spotify tracks; make sure "
                "SPOTIFY_CHECK_PLAYLISTS has one or more keys from "
                "spotify_playlists.json"
            )
        else:
            track_sets.append((tracks, "Spotify Playlist Tracks"))
    if config.get("LOCAL_CHECK_DIRS"):
        tracks = get_local_tracks(config)
        if not tracks:
            logger.warning(
                "There are no local tracks; make sure LOCAL_CHECK_DIRS has "
                'one or more directories containing one or more tracks'
            )
        else:
            track_sets.append((tracks, "Local Directory Tracks"))

    if not track_sets:
        return beatcloud_tracks, beatcloud_matches

    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks()
    
    path_lookup = {
        os.path.splitext(os.path.basename(x))[0]: x for x in beatcloud_tracks
    }
    
    for tracks, track_type in track_sets:
        matches = find_matches(
            tracks,
            path_lookup.keys(),
            config,
        )
        logger.info(f"\n{track_type} / Beatcloud Matches: {len(matches)}")
        for loc, matches in groupby(
            sorted(matches, key=itemgetter(0)), key=itemgetter(0)
        ):
            logger.info(f"{loc}:")
            for _, track, beatcloud_track, fuzz_ratio in matches:
                beatcloud_matches.append(path_lookup[beatcloud_track])
                logger.info(f"\t{fuzz_ratio}: {track} | {beatcloud_track}")
    
    return beatcloud_tracks, beatcloud_matches


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

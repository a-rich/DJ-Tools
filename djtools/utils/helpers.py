"""This module contains helper functions that are not specific to any
particular sub-package of this library.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps
import inspect
from itertools import product
import logging
import logging.config
import os
import pathlib
from pathlib import Path
from subprocess import check_output
import typing
from typing import Callable, Dict, List, Set, Tuple

from fuzzywuzzy import fuzz
import spotipy
from tqdm import tqdm

from djtools.configs.config import BaseConfig
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
    ret = ()
    fuzz_ratio = fuzz.ratio(spotify_track, beatcloud_track)
    if fuzz_ratio >= threshold:
        ret = spotify_playlist, spotify_track, beatcloud_track, fuzz_ratio
    return ret


def find_matches(
    spotify_tracks: Dict[str, Set[str]],
    beatcloud_tracks: List[str],
    config: BaseConfig,
) -> List[Tuple[str, float]]:
    """Computes the Levenshtein similarity between the product of all beatcloud
        tracks with all the tracks in the given Spotify playlist(s) and returns
        those that match above a threshold.

    Args:
        spotify_tracks: Spotify track titles and artist names.
        beatcloud_tracks: Beatcloud track titles and artist names.
        config: Configuration object.

    Returns:
        List of tuples of Spotify playlist, Spotify track, Beatcloud track, and
            Levenshtein distance.
    """
    spotify_tracks = [
        (playlist, track) for playlist, tracks in spotify_tracks.items()
        for track in tracks
    ]
    _product = list(product(spotify_tracks, beatcloud_tracks))
    _temp, beatcloud_tracks = zip(*_product)
    spotify_playlists, spotify_tracks = zip(*_temp)
    fuzz_ratio = config.CHECK_TRACKS_FUZZ_RATIO
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
    cmd = ["aws", "s3", "ls", "--recursive", "s3://dj.beatcloud.com/dj/music/"]
    output = check_output(cmd).decode("utf-8").split("\n")
    tracks = [Path(track) for track in output if track]
    logger.info(f"Got {len(tracks)} tracks from the beatcloud")

    return tracks


def get_local_tracks(config: BaseConfig) -> Dict[str, List[str]]:
    """Aggregates the files from one or more local directories in a dictionary
        mapped with parent directories.

    Args:
        config: Configuration object.

    Returns:
        Local file names keyed by parent directory.
    """
    local_dir_tracks = {}
    for _dir in config.LOCAL_DIRS:
        if not _dir.exists():
            logger.warning(
                f"{_dir} does not exist; will not be able to check its "
                "contents against the beatcloud"
            )
            continue
        files = list(_dir.rglob("**/*.*"))
        if files:
            local_dir_tracks[_dir] = files
    local_tracks_count = sum(len(x) for x in local_dir_tracks.values())
    logger.info(f"Got {local_tracks_count} files under local directories")

    return local_dir_tracks


def get_playlist_tracks(
    spotify: spotipy.Spotify, playlist_id: str) -> List[Dict]:
    """Queries Spotify API for a playlist and pulls tracks from it.

    Args:
        spotify: Spotify client.
        playlist_id: Playlist ID of Spotify playlist to pull tracks from.

    Raises:
        RuntimeError: Playlist_id must correspond with a valid Spotify playlist.

    Returns:
        List of Spotify track results.
    """
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception:
        raise RuntimeError(
            f"Failed to get playlist with ID {playlist_id}"
        ) from Exception

    result = playlist["tracks"]
    tracks = list(result["items"])
    while result["next"]:
        result = spotify.next(result)
        tracks.extend(list(result["items"]))

    return tracks


def get_spotify_tracks(
    config: BaseConfig, playlists: List[str]
) -> Dict[str, List[Dict]]:
    """Aggregates the tracks from one or more Spotify playlists into a
        dictionary mapped with playlist names.

    Args:
        config: Configuration object.
        playlists: List of Spotify playlist name.

    Returns:
        Spotify tracks keyed by playlist name.
    """
    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()

    playlist_tracks = {}
    _sum = 0
    for playlist in playlists:
        playlist_id = playlist_ids.get(playlist)
        if not playlist_id:
            logger.error(f"{playlist} not in spotify_playlists.yaml")
            continue
        playlist_tracks[playlist] = get_playlist_tracks(spotify, playlist_id)
        length = len(playlist_tracks[playlist])
        logger.info(
            f'Got {length} track{"" if length == 1 else "s"} from Spotify '
            f'playlist "{playlist}"'
        )
        _sum += length

        if config.VERBOSITY > 0:
            for track in playlist_tracks[playlist]:
                logger.info(f"\t{track}")
    logger.info(
        f'Got {_sum} track{"" if _sum == 1 else "s"} from Spotify in total'
    )

    return playlist_tracks


def initialize_logger() -> Tuple[logging.Logger, str]:
    """Initializes logger from configuration.

    Returns:
        Tuple containing Logger and associated log file.
    """
    log_file = (
        Path(__file__).parent.parent / "logs" /
        f'{datetime.now().strftime("%Y-%m-%d")}.log'
    )
    log_conf = Path(__file__).parent.parent / "configs" / "logging.conf"
    logging.config.fileConfig(
        fname=log_conf,
        # NOTE(a-rich): the `logfilename` needs a unix-style path.
        defaults={"logfilename": log_file.as_posix()},
        disable_existing_loggers=False,
    )

    return logging.getLogger(__name__), log_file


def make_path(func: Callable) -> Callable:
    """Decorator for converting Path-typed args to Paths.

    Args:
        func: Callable being decorated with this function.

    Raises:
        RuntimeError: args annotated with a pathlib.Path need to be able to
            have Paths created from them.
        RuntimeError: kwargs annotated with a pathlib.Path need to be able to
            have Paths created from them.

    Returns:
        The Callable being wrapped by this decorator.
    """
    @wraps(make_path)
    def str_to_path(*args, **kwargs):
        """Converts non-Path type args into Paths if annotated as Paths.

        Raises:
            RuntimeError: args annotated with a pathlib.Path need to be able to
                have Paths created from them.
            RuntimeError: kwargs annotated with a pathlib.Path need to be able
                to have Paths created from them.
        """
        # Get the function's type annotations and partition them by args and
        # kwargs.
        path_types = (pathlib.Path, typing.Union[pathlib.Path, None])
        num_args= 0
        num_kwargs = 0
        type_hints = list(typing.get_type_hints(func).values())
        sig = inspect.signature(func)
        for parameter in sig.parameters.values():
            if parameter.name == "self":
                type_hints.insert(0, "self")
            if parameter.name in kwargs:
                num_kwargs += 1
            else:
                num_args += 1
        arg_type_hints = type_hints[:num_args]
        kwarg_type_hints = type_hints[:num_kwargs]

        # Convert each arg to a Path if the annotation type is pathlib.Path.
        args = list(args)
        for index, (arg, arg_type) in enumerate(zip(args, arg_type_hints)):
            # Skip if the arg shouldn't be a path or it should be a Path but
            # already is.
            if arg_type not in path_types or (
                arg_type in path_types and isinstance(arg, Path)
            ):
                continue

            try:
                args[index] = Path(arg)
            except Exception as exc:
                raise RuntimeError(
                    "Error creating Path in function "
                    f'"{func.__name__}" from positional arg "{arg}" annotated '
                    f'with type "{arg_type}": {exc}'
                ) from Exception
        args = tuple(args)

        # Convert each kwarg to a Path if the annotation type is pathlib.Path.
        for (key, value), arg_type in zip(kwargs.items(), kwarg_type_hints):
            # Skip if the arg value shouldn't be a path or it should be a Path
            # but already is.
            if arg_type not in path_types or (
                arg_type in path_types and isinstance(value, Path)
            ):
                continue

            try:
                kwargs[key] = Path(value)
            except Exception as exc:
                raise RuntimeError(
                    "Error creating Path in function "
                    f'"{func.__name__}" from keyword arg "{key}={value}" '
                    f'annotated with type "{arg_type}": {exc}'
                ) from Exception

        return func(*args, **kwargs)

    return str_to_path


def reverse_title_and_artist(path_lookup: Dict[str, str]) -> Dict[str, str]:
    """Reverses the title and artist parts of the filename.

    Args:
        path_lookup: Mapping of filenames to file paths.

    Returns:
        Mapping with the title and artist in the filenames reversed.
    """
    new_path_lookup = {}
    for key, value in path_lookup.items():
        split = key.split(" - ")
        title = " - ".join(split[:-1])
        artist = split[-1]
        new_path_lookup[f"{artist} - {title}"] = value

    return new_path_lookup

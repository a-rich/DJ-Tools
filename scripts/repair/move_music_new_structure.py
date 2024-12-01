"""Script used to relocate all music files from the old genre-top-level
structure to the new username-top-level structure.
"""

# pylint: disable=too-many-arguments,duplicate-code,no-member
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
import json
import logging
import logging.config
from operator import itemgetter
import os
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth

for logger in ["spotipy", "urllib3"]:
    logger = logging.getLogger(logger)
    logger.setLevel(logging.CRITICAL)

parent = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
log_conf = os.path.join(
    parent, "src", "djtools", "configs", "logging.conf"
).replace(os.sep, "/")
logging.config.fileConfig(
    fname=log_conf,
    disable_existing_loggers=False,
    defaults={"logfilename": "move_music_new_structure.log"},
)
logger = logging.getLogger(__name__)


def get_spotify_tracks(_config, spotify_playlists):
    """Aggregates the tracks from one or more Spotify playlists into a
    dictionary mapped with track title and artist names.

    Args:
        _config (dict): configuration object
        spotify_playlists (dict): playlist names and IDs

    Returns:
        (dict): Spotify tracks keyed by titles and artist names
    """

    spotify = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=_config["spotify_client_id"],
            client_secret=_config["spotify_client_secret"],
            redirect_uri=_config["spotify_redirect_uri"],
            scope="playlist-modify-public",
        )
    )
    _tracks = {}
    for playlist, playlist_id in spotify_playlists.items():
        logger.info(f'Getting tracks from Spotify playlist "{playlist}"...')
        __tracks = get_playlist_tracks(spotify, playlist_id, playlist)
        logger.info(f"Got {len(__tracks)} tracks from {playlist}")
        _tracks.update(__tracks)

    logger.info(f"Got {len(_tracks)} tracks in total")

    return _tracks


def get_playlist_tracks(spotify, playlist_id, _playlist):
    """Queries Spotify API for a playlist and pulls tracks from it.

    Args:
        spotify (spotipy.Spotify): Spotify client
        playlist_id (str): playlist ID of Spotify playlist to pull tracks from

    Raises:
        RuntimeError: playlist_id must correspond with a valid Spotify playlist

    Returns:
        set: Spotify track titles and artist names from a given playlist
    """
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception:
        raise RuntimeError(
            f"Failed to get playlist with ID {playlist_id}"
        ) from Exception

    result = playlist["tracks"]
    _tracks = add_tracks(result, _playlist)

    while result["next"]:
        result = spotify.next(result)
        _tracks.update(add_tracks(result, _playlist))

    return _tracks


def add_tracks(result, playlist):
    """Parses a page of Spotify API result tracks and returns a list of the
    track titles and artist names.

    Args:
        result (spotipy.Tracks): paged result of Spotify tracks

    Returns:
        (list): Spotify track titles and artist names
    """
    _tracks = {}
    for track in result["items"]:
        title = track["track"]["name"]
        artists = ", ".join([y["name"] for y in track["track"]["artists"]])
        _tracks[f"{title} - {artists}"] = {
            "added_at": track["added_at"],
            "added_by": track["added_by"]["id"],
            "playlist": playlist,
        }

    return _tracks


def get_beatcloud_tracks():
    """Lists all the music files in S3 and parses out the track titles and
    artist names.

    Returns:
        list: beatcloud track titles and artist names
    """
    logger.info("Getting tracks from the beatcloud...")
    cmd = "aws s3 ls --recursive s3://dj.beatcloud.com/dj/music/"
    with os.popen(cmd) as proc:
        output = proc.read().split("\n")
    _tracks = [track.split("dj/music/")[-1] for track in output if track]
    logger.info(f"Got {len(_tracks)} tracks")

    return _tracks


def analyze_tracks(_tracks, users):
    """Display Spotify tracks grouped by user and then playlists.

    Args:
        _tracks (dict): map Spotify track - artist -> {added_by, playlist}
        users (dict): map Spotify username -> beatcloud username
    """
    logger.info("Analyzing user contributions to spotify playlists...")
    for user_group_id, user_group in groupby(
        sorted(_tracks.values(), key=itemgetter("added_by")),
        key=itemgetter("added_by"),
    ):
        logger.info(f"{users[user_group_id]} ({user_group_id}):")
        for playlist_group_id, playlist_group in groupby(
            sorted(user_group, key=itemgetter("playlist")),
            key=itemgetter("playlist"),
        ):
            playlist_group = list(playlist_group)
            logger.info(f"\t{playlist_group_id}: {len(playlist_group)}")


def find_local_files(usb_path, remote_files):
    """Validates that each remote file exists locally. Returns the full paths
    of just the validated ones.

    Args:
        usb_path (str): full path to root of USB drive with "DJ Music"
        remote_files (list): list of `beatcloud` files relative to "/dj/music/"

    Returns:
        list: paths to local files that are also in the `beatcloud`
    """
    payload = [[usb_path] * len(remote_files), remote_files]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        _files = list(
            filter(None, list(executor.map(exists_process, *payload)))
        )
    logger.info(f"Found {len(_files)} local files")

    return _files


def exists_process(path, _file):
    """Threaded process that returns the local path, if it exists, to a track
    that exists in the `beatcloud`.

    Args:
        path (str): usb_path
        _file (str): sub-path to beatcloud track (relative to "/dj/music/")

    Returns:
        str: local path to track that exists in the `beatcloud`
    """
    _path = os.path.join(path, "DJ Music", _file).replace(os.sep, "/")

    return _file if os.path.exists(_path) else None


def fix_files(bad_files, _local_files, move_local_files, usb_path, verbosity):
    """Renames local files to fix typos and improve fuzz match results so all
    correct matches happen above the final fuzz_ratio.

    Args:
        bad_files (dict): map bad file names to their corrections
        _local_files (list): list of local file paths
        move_local_files (bool): flag to trigger moving local files
        usb_path (str): path to root of USB containing "DJ Music"
        verbosity (int): verbosity level

    Returns:
        list: _local_files after swapping bad files for their corrections
    """
    logger.info(f'Renaming {len(bad_files)} "bad files"...')
    for bad, good in bad_files.items():
        _bad = os.path.join(usb_path, "DJ Music", bad).replace(os.sep, "/")
        _good = os.path.join(usb_path, "DJ Music", good).replace(os.sep, "/")
        if verbosity > 0:
            logger.info(f"\t{_bad} -> {_good}")
        if move_local_files:
            try:
                os.rename(_bad, _good)
            except Exception as exc:
                logger.error(f'failed to rename "{_bad}" to "{_good}": {exc}')
                continue
        try:
            _index = _local_files.index(bad)
            _local_files[_index] = good
        except Exception:
            continue

    return _local_files


def match_local_files(
    _local_files,
    _tracks,
    fuzz_ratio,
    verbosity,
    ignore,
    _matches,
    cache_fuzz_results,
):
    """Matches local files to Spotify tracks:
        (1) first pass does direct string equality checks between file names
            and `title - artist` strings of Spotify tracks
        (2) second pass fuzzy matches files against Spotify tracks...

    If run with `--cache_fuzz_results`, previously confirmed matches are
    eliminated from consideration during fuzzy matching; this is so it can be
    easier to dial in the proper `fuzz_ratio` while ensuring every matched
    track is correct (and also identify what `bad_files` can be corrected to
    improve matching). The final run should NOT use cached fuzz results.

    Args:
        _local_files (list): list of local file paths
        _tracks (dict): map Spotify track - artist -> {added_by, playlist}
        fuzz_ratio (int): min fuzz ratio to accept file -> Spotify track match
        verbosity (int): verbosity level
        ignore (list): true non-matches with fuzz ratio above "fuzz_ratio"
        _matches (dict): temporary lookup that functions like "ignore"
        cache_fuzz_results (bool): whether or not to populate the fuzz results
                                   cache and ignore results already present in
                                   said cache

    Returns:
        tuple: (map: file path -> Spotify track, list: files not mapped)
    """
    # filter local files by those that can directly be mapped to one of the
    # spotify tracks; also remove the corresponding Spotify tracks from future
    # consideration
    found_tracks = {}
    __local_files = []
    for _file in _local_files:
        name = os.path.splitext(os.path.basename(_file))[0]
        track = _tracks.get(name)
        if not track:
            __local_files.append(_file)
            continue
        del _tracks[name]
        found_tracks[_file] = track
    _local_files = __local_files
    directly_found = len(found_tracks)
    logger.info(
        f"Found {directly_found} tracks...fuzzy searching for "
        f"the remaining {len(_local_files)}"
    )

    # Load cached fuzzy search results...
    # This tool is intended to be used in iterations with progressively lower
    # minimum 'fuzz_ratio' so as to:
    #    - first fix local files with typos or misformattings (correction
    #      mapping in data['bad_files'])
    #    - then verify that every local track pairs properly with the most
    #      similar Spotify track
    #    - once invalid matches start showing up in the results, make sure each
    #      one is definitely not traceable to a Spotify playlist and then add
    #      to data['ignore']
    #
    # Each iteration should actually be a two-stage process:
    #    (1) see results at newly lowered 'fuzz_ratio', using
    #        `.fuzz_cache.json` to filter previous results, and make any
    #        necessary additions to data['bad_files'] and / or data['ignore']
    #    (2) restore `.fuzz_cache.json` to the backup you made before (1) and
    #        confirm the output at the same 'fuzz_ratio' is as expected...
    #
    # Once all results are definitely not a match at 'fuzz_ratio=0', then
    # you've confirmed every local file that can be attributed to a recognized
    # user of data['users']; what remains outside of the username-based folders
    # came from outside of data['spotify_playlists'] or else is an artifact
    # from a time when the beatcloud contained incorrectly named files that had
    # since been corrected.
    if cache_fuzz_results and os.path.exists(".fuzz_cache.json"):
        with open(".fuzz_cache.json", encoding="utf-8") as _file:
            cached_fuzz_results = json.load(_file)
        logger.info(
            f"Ignoring {len(cached_fuzz_results)} fuzz results "
            "previously matched"
        )
        prev_track_count = len(_tracks)
        prev_matches = set(cached_fuzz_results.values())
        _tracks = {k: v for k, v in _tracks.items() if k not in prev_matches}
        logger.info(
            f"Reduced number of Spotify tracks being considered "
            f"from {prev_track_count} to {len(_tracks)}"
        )
    else:
        cached_fuzz_results = {}

    # distribute fuzzy search of a file against every Spotify track...keep the
    # most similar result above 'fuzz_ratio' and add it to the collection of
    # directly matched files -> tracks
    not_matched = []
    ignore = {os.path.splitext(os.path.basename(x))[0] for x in ignore}
    for _file in _local_files:
        name = os.path.splitext(os.path.basename(_file))[0]
        if any((name in x for x in [cached_fuzz_results, ignore, _matches])):
            continue
        payload = [
            [name] * len(_tracks),
            list(_tracks.keys()),
            [fuzz_ratio] * len(_tracks),
        ]
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
            __matches = sorted(
                filter(None, executor.map(fuzz_process, *payload)),
                reverse=True,
                key=itemgetter(1),
            )
        if not __matches:
            not_matched.append(_file)
            continue
        match, ratio = __matches[0]
        found_tracks[_file] = _tracks[match]
        found_tracks[_file]["fuzz_ratio"] = ratio
        found_tracks[_file]["match"] = match
        # del _tracks[match]
        if cache_fuzz_results:
            cached_fuzz_results[name] = match

    if cache_fuzz_results:
        with open(".fuzz_cache.json", "w", encoding="utf-8") as _file:
            json.dump(cached_fuzz_results, _file)

    # optionally display all the results of the fuzzy search
    if verbosity > 0:
        logger.info("Fuzzy matched files:")
        for name, track in found_tracks.items():
            if not track.get("fuzz_ratio"):
                continue
            logger.info(
                f"\t{track['fuzz_ratio']}: "
                + os.path.splitext(os.path.basename(name))[0]
            )
            logger.info(f"\t    {track['match']}")
    logger.info(f"Fuzzy matched {len(found_tracks) - directly_found} files")
    logger.info(
        f"Unable to find {len(not_matched)} tracks (plus the "
        f"{len(ignore)} in data['ignore'])"
    )

    return found_tracks, not_matched


def move_files(
    found_tracks,
    not_matched,
    users,
    playlist_genres,
    usb_path,  # pylint: disable=too-many-arguments,too-many-locals
    move_local_files,
    not_matched_lookup,
    move_remote_files,
    verbosity,
    ignore,
    bad_files_inverse_lookup,
    xml_path,
    _user_names,
    write_xml,
):
    """Moves files to their new location...
        (1) direct matches and fuzzy match results are moved locally
        (2) not matched local files are moved based on their previous directory
        (3) S3 files are moved from former location to new location

    Args:
        found_tracks (dict): map file path -> Spotify track
        not_matched (list): files not matched to Spotify track
        users (dict): map Spotify username -> beatcloud username
        playlist_genres (dict): map playlist name to genre folder
        usb_path (str): full path to root of USB drive with "DJ Music"
        move_local_files (bool): flag to trigger moving local files
        not_matched_lookup (dict): maps local directories to genre folder
        move_remote_files (bool): flag to trigger moving s3 files
        verbosity (int): verbosity level
        ignore (list): true non-matches with fuzz ratio above "fuzz_ratio"
        bad_files_inverse_lookup (dict): reverse lookup of corrected
                                         "bad_files"...used to move incorrect
                                         version of file in S3 to new corrected
                                         location
        xml_path (str): path to Rekordbox XML; will be rewritten so tracks
                        point to their new locations
    """
    # move every local file matched with a playlist and user to that user's
    # corresponding data['playlist_genres'] folder
    s3_prefix = "s3://dj.beatcloud.com/dj/music/"
    s3_moves = []
    logger.info("Moving matched local files to their new locations...")
    for name, track in found_tracks.items():
        user = users[track["added_by"]]
        genre = playlist_genres[track["playlist"]]
        base_path = os.path.join(user, genre, "old", os.path.basename(name))
        dest_path = os.path.join(usb_path, "DJ Music", base_path).replace(
            os.sep, "/"
        )
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            if move_local_files:
                make_dirs(dest_dir)
        src_path = os.path.join(usb_path, "DJ Music", name).replace(
            os.sep, "/"
        )
        msg = f"\t{src_path} -> {dest_path}"
        if verbosity > 0:
            logger.info(msg)
        if move_local_files:
            try:
                os.rename(src_path, dest_path)
            except Exception as exc:
                logger.error(
                    f'failed to move matched file "{src_path}" to '
                    f'"{dest_path}": {exc}'
                )
                continue

        # reformat paths for S3 file relocations
        name = bad_files_inverse_lookup.get(name, name)
        src_path = os.path.join(s3_prefix, name).replace(os.sep, "/")
        dest_path = os.path.join(s3_prefix, base_path).replace(os.sep, "/")
        s3_moves.append((src_path, dest_path))

    # move remaining tracks using the original file location's parent directory
    # to determine the proper new location
    logger.info(
        "Moving unmatched local files to the proper location based "
        "on the directory of their previous location..."
    )
    for name in not_matched + ignore:
        parent_dir = os.path.basename(os.path.dirname(name))
        base_path = os.path.join(
            not_matched_lookup[parent_dir], "old", os.path.basename(name)
        )
        dest_path = os.path.join(usb_path, "DJ Music", base_path).replace(
            os.sep, "/"
        )
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            if move_local_files:
                make_dirs(dest_dir)
        src_path = os.path.join(usb_path, "DJ Music", name).replace(
            os.sep, "/"
        )
        msg = f"\t{src_path} -> {dest_path}"
        if verbosity > 0:
            logger.info(msg)
        if move_local_files:
            try:
                os.rename(src_path, dest_path)
            except Exception as exc:
                logger.error(
                    f'failed to move unmatched file "{src_path}" '
                    f'to "{dest_path}": {exc}'
                )
                continue

        # reformat paths for S3 file relocations
        name = bad_files_inverse_lookup.get(name, name)
        src_path = os.path.join(s3_prefix, name).replace(os.sep, "/")
        dest_path = os.path.join(s3_prefix, base_path).replace(os.sep, "/")
        s3_moves.append((src_path, dest_path))

    # Move S3 files to their new locations
    logger.info(f"Moving {len(s3_moves)} S3 files to new locations...")
    cmd = 'aws s3 mv "{}" "{}"'
    xml_lookup = {}
    for src, dst in s3_moves:
        _cmd = cmd.format(src, dst)
        if move_remote_files:
            os.system(_cmd)
        elif verbosity > 0:
            logger.info(f"\t{_cmd}")
        xml_lookup[src.split(s3_prefix)[-1]] = dst.split(s3_prefix)[-1]

    # rewrite XML_PATH so tracks point to their new locations
    if write_xml:
        with open(xml_path, encoding="utf-8") as _file:
            soup = BeautifulSoup(_file.read(), "xml")
        loc_prefix = os.path.join(
            "file://localhost", usb_path.strip("/"), "DJ Music", ""
        ).replace(os.sep, "/")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            loc = unquote(track["Location"]).split(loc_prefix)[-1]
            if any((loc.startswith(name) for name in _user_names)):
                continue
            track["Location"] = quote(
                os.path.join(loc_prefix, xml_lookup[loc]).replace(os.sep, "/")
            )

        with open(
            xml_path, mode="wb", encoding=soup.orignal_encoding
        ) as _file:
            _file.write(soup.prettify("utf-8"))


def fuzz_process(file_name, track_name, threshold):
    """Threaded fuzzy search between local file name and Spotify track.

    Args:
        file_name (str): local file name
        track_name (str): spotify track title - artist
        threshold (int): min fuzz ratio to accept file -> Spotify track match

    Returns:
        tuple: (Spotify track title - artist, fuzz ratio with local file)
    """
    ret = ()
    fuzz_ratio = fuzz.ratio(file_name.lower(), track_name.lower())
    if fuzz_ratio >= threshold:
        ret = (track_name, fuzz_ratio)
    return ret


def make_dirs(dest):
    """Creates non-existent directory.

    Args:
        dest (str): directory to create
    """
    if os.name == "nt":
        cwd = os.getcwd()
        path_parts = dest.split("/")
        root = path_parts[0]
        path_parts = path_parts[1:]
        os.chdir(root)
        for part in path_parts:
            os.makedirs(part, exist_ok=True)
            os.chdir(part)
        os.chdir(cwd)
    else:
        os.makedirs(dest, exist_ok=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--structure_data",
        required=True,
        help="""JSON with keys:' \
                "spotify_playlists": map playlist_name -> playlist_id
                "playlist_genres": map playlist name -> genre folder
                "users": map Spotify username -> beatcloud username
                "not_matched_genre_lookup": map remainder track folders -> new
                                            folders
                "bad_files": map badly named files -> corrections
                "ignore": list of files that incorrectly match Spotify tracks
                          above the final fuzz_ratio""",
    )
    parser.add_argument("--config_path", help="path to config.json")
    parser.add_argument(
        "--fuzz_ratio",
        default=80,
        type=float,
        help="minimum fuzz ratio to match Spotify track to local file",
    )
    parser.add_argument(
        "--cache_fuzz_results",
        action="store_true",
        help="cache fuzz matches that are supposedly correct...used to "
        "clean up output as fuzz ratio is progressively lowered",
    )
    parser.add_argument(
        "--move_local_files",
        action="store_true",
        help="actual execute local file moves",
    )
    parser.add_argument(
        "--move_remote_files",
        action="store_true",
        help="rename files in S3 so they're under the proper user and "
        "genre folders",
    )
    parser.add_argument(
        "--write_xml",
        action="store_true",
        help="rewrite XML_PATH to fix locations of tracks",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="logging verbosity",
    )
    args = parser.parse_args()

    if not os.path.exists(args.structure_data):
        raise RuntimeError(
            f"required `--structure_data` JSON config "
            f"'{args.structure_data}' doesn't exist"
        )

    with open(args.structure_data, encoding="utf-8") as _file:
        data = json.load(_file)

    # validate all bad_file lookups have .mp3 extensions
    data["bad_files_inverse_lookup"] = {}
    for key, value in data["bad_files"].items():
        if any((not x.endswith(".mp3") for x in [key, value])):
            raise ValueError(f'"{key, value}" must end with ".mp3"')
        data["bad_files_inverse_lookup"][value] = key

    # temporary buffer to hold local file results for special consideration
    # while fuzzy searching
    _matches = {}

    # standard djtools 'config.json' file (for usb_path, aws_profile, etc.)
    with open(args.config_path, encoding="utf-8") as _file:
        config = json.load(_file)

    if args.move_remote_files:
        os.environ["AWS_PROFILE"] = config.get("aws_profile")

    # cached Spotify API results and `aws s3 ls --recursive` on 'dj/music/'
    cache_path = os.path.join(
        os.path.dirname(__file__), ".cache.json"
    ).replace(os.sep, "/")

    if not os.path.exists(cache_path):
        tracks = get_spotify_tracks(config, data["spotify_playlists"])
        files = get_beatcloud_tracks()
        with open(cache_path, "w", encoding="utf-8") as _file:
            json.dump({"tracks": tracks, "files": files}, _file)
    else:
        with open(cache_path, encoding="utf-8") as _file:
            cache = json.load(_file)
            tracks = cache["tracks"]
            files = cache["files"]
        logger.info(
            f"Retrieved {len(tracks)} tracks and {len(files)} files "
            "from cache."
        )

    # display data['users'] contributions to data['spotify_playlists']
    analyze_tracks(tracks, data["users"])

    # filter `aws s3 ls` result for those that exist at config['usb_path']
    local_files = find_local_files(config["usb_path"], files)

    # optionally display the beatcloud files that aren't present locally
    if args.verbosity > 0:
        unfound = set(files).difference(set(local_files))
        logger.info(f"{len(unfound)} files in S3 not found locally:")
        for _file in unfound:
            logger.info(f"\t{_file}")

    # don't consider any files already in the proper username-based folders
    user_names = {
        os.path.join(x, "").replace(os.sep, "/")
        for x in data["users"].values()
    }
    _ = len(local_files)
    local_files = [
        x
        for x in local_files
        if not any((x.startswith(name) for name in user_names))
    ]
    logger.info(
        f"Ignoring {_ - len(local_files)} files that are already "
        "in the right place"
    )

    # rename files (only if `--move_local_files`), otherwise swaps 'bad' local
    # files in index for the 'good' ones mapped in data['bad_files']
    local_files = fix_files(
        data["bad_files"],
        local_files,
        args.move_local_files,
        config["usb_path"],
        args.verbosity,
    )

    # This operation is meant to be run multiple times with progressively lower
    # 'fuzz_ratio'...each time:
    #    - typos and misformattings should be corrected using data['bad_files']
    #    - correct matches should be allowed to cache in `.fuzz_cache.json`
    #    - incorrect matches must be confirmed unattributable to a user and
    #      added to data['ignore']; incorrect matches that are permitted may
    #      result in a track being moved to a technically incorrect user /
    #      genre folder
    _found_tracks, _not_matched = match_local_files(
        local_files,
        tracks,
        args.fuzz_ratio,
        args.verbosity,
        data["ignore"],
        _matches,
        args.cache_fuzz_results,
    )

    # moves local files, remote files, and rewrites XML
    move_files(
        _found_tracks,
        _not_matched,
        data["users"],
        data["playlist_genres"],
        config["usb_path"],
        args.move_local_files,
        data["not_matched_genre_lookup"],
        args.move_remote_files,
        args.verbosity,
        data["ignore"],
        data["bad_files_inverse_lookup"],
        config["XML_PATH"],
        user_names,
        args.write_xml,
    )

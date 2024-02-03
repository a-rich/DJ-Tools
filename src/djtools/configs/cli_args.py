"""This module is responsible for creating the argparse.NameSpace object from
the CLI args.
"""

from argparse import Action, ArgumentParser, Namespace, RawTextHelpFormatter
import json
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union


def get_arg_parser() -> ArgumentParser:
    """Build an argparse.ArgumentParser object.

    Returns:
        ArgumentParser object.
    """
    parser = ArgumentParser(
        description=(
            "djtools is a Python library with many features for streamlining "
            "the processes around collecting, curating, and sharing a music "
            "collection.\n\nRun djtools with one of the four available "
            "sub-commands: collection, spotify, sync, utils"
        ),
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "--link-configs",
        type=_convert_to_paths,
        help=(
            "The configuration files used by djtools are included at the "
            "location where this package is installed...\nUse this option to "
            "symbolically link them to a more accessible location for easier "
            "editing.\nNote, the directory you're linking to must not already "
            "exist."
        ),
    )
    parser.add_argument(
        "--artist-first",
        action="store_true",
        help=(
            "Indicate that Beatcloud tracks are in the format "
            '"Artist - Track Title" instead of "Track Title - Artist".\nThe '
            "ordering is important for any operation that compares your "
            "tracks' filenames with Spotify tracks or other files...\n"
            'This includes "--spotify-playlist-from-upload", '
            '"--download-spotify-playlist", "--spotify-playlists", and '
            '"--check-tracks".'
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logger level.",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="Increase the logging verbosity.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display the version number of the installed djtools.",
    )
    subparsers = parser.add_subparsers(title="sub-commands")

    ###########################################################################
    # Sub-command for the collection package.
    ###########################################################################
    collection_parser = subparsers.add_parser(
        name="collection",
        help=(
            "Perform operations on your DJ collection such as building "
            "playlists based on your tags, shuffling track numbers, and "
            "copying playlists to another location."
        ),
        formatter_class=RawTextHelpFormatter,
    )
    collection_parser.add_argument(
        "--collection-path",
        type=_convert_to_paths,
        help='Path to a collection database (e.g. "rekordbox.xml").',
    )
    collection_parser.add_argument(
        "--collection-playlist-filters",
        type=str,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "PlaylistFilter implementations to apply with "
            '"--collection-playlists"'
        ),
    )
    collection_parser.add_argument(
        "--collection-playlists",
        action="store_true",
        help="Flag to trigger building collection playlists.",
    )
    collection_parser.add_argument(
        "--collection-playlists-remainder",
        type=str,
        choices=["folder", "playlist"],
        help=(
            "If there are tags not included in your "
            '"collection_playlists.yaml", the associated tracks are '
            'automatically pushed into either an "Other" folder of playlists '
            '(one for each tag) or an "Other" playlist based on this option.'
        ),
    )
    collection_parser.add_argument(
        "--copy-playlists",
        type=str,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "By providing a list of playlist names, this option will:\n  - "
            "copy the audio files in those playlists to "
            '"--copy-playlists-destination"\n  - create a new collection with '
            "just those playlists where the tracks contained in them have "
            "updated locations"
        ),
    )
    collection_parser.add_argument(
        "--copy-playlists-destination",
        type=_convert_to_paths,
        help="Location to copy playlists' audio files to.",
    )
    collection_parser.add_argument(
        "--platform",
        type=str,
        choices=["rekordbox"],
        help='DJ platform used for the collection package (e.g. "rekordbox").',
    )
    collection_parser.add_argument(
        "--shuffle-playlists",
        type=str,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "By providing a list of playlist names, this option will write to "
            "the track number attribute to emulate shuffling of the tracks."
        ),
    )

    ###########################################################################
    # Sub-command for the spotify package.
    ###########################################################################
    spotify_parser = subparsers.add_parser(
        name="spotify",
        help=(
            "Build playlists in Spotify either from:\n  - posts in the "
            'subreddits configured with "--spotify-playlist-subreddits"\n  - '
            'the output generated by a user running "--upload-music" with the '
            '"--discord-url" option configured'
        ),
        formatter_class=RawTextHelpFormatter,
    )
    spotify_parser.add_argument(
        "--reddit-client-id",
        type=str,
        help="Reddit API client ID.",
    )
    spotify_parser.add_argument(
        "--reddit-client-secret",
        type=str,
        help="Reddit API client secret.",
    )
    spotify_parser.add_argument(
        "--reddit-user-agent",
        type=str,
        help="Reddit API user agent.",
    )
    spotify_parser.add_argument(
        "--spotify-client-id",
        type=str,
        help="Spotify API client ID.",
    )
    spotify_parser.add_argument(
        "--spotify-client-secret",
        type=str,
        help="Spotify API client secret.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-default-limit",
        type=int,
        help="Default number of tracks for a Spotify playlist.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-default-period",
        type=str,
        help="Default subreddit time filter for a Spotify playlist.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-default-type",
        type=str,
        help="Default subreddit post filter for a Spotify playlist.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-from-upload",
        action="store_true",
        help=(
            "Flag to trigger building a Spotify playlist using the copied "
            "Discord webhook output of a music upload."
        ),
    )
    spotify_parser.add_argument(
        "--spotify-playlist-fuzz-ratio",
        type=int,
        help="Minimum similarity to add track to a playlist.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-post-limit",
        type=int,
        help="Maximum subreddit posts to query for each playlist.",
    )
    spotify_parser.add_argument(
        "--spotify-playlist-subreddits",
        type=_parse_json,
        help=(
            "List of subreddits configs to build playlists from.\nFormat as "
            'a JSON string containing a list of dictionaries with "name", '
            '"type", "period", and "limit" keys.\nNote: "name" is required '
            "while the other keys are optional.\nExample:\n  "
            '\'[{"name": "jungle"}, {"name": "techno", "type": "top", '
            '"period": "week", "limit": 75}]\''
        ),
    )
    spotify_parser.add_argument(
        "--spotify-playlists",
        action="store_true",
        help="Flag to trigger building Spotify playlists.",
    )
    spotify_parser.add_argument(
        "--spotify-redirect-uri",
        type=str,
        help="Spotify API redirect URI.",
    )
    spotify_parser.add_argument(
        "--spotify-username",
        type=str,
        help="Spotify user to build playlists for.",
    )

    ###########################################################################
    # Sub-command for the sync package.
    ###########################################################################
    sync_parser = subparsers.add_parser(
        name="sync",
        help=(
            'Sync audio files and DJ collections between your "--usb-path" '
            "and the Beatcloud."
        ),
        formatter_class=RawTextHelpFormatter,
    )
    sync_parser.add_argument(
        "--aws-profile",
        type=str,
        help="AWS config profile.",
    )
    sync_parser.add_argument(
        "--aws-use-date-modified",
        action="store_true",
        help=(
            'Drop the "--size-only" flag for "aws s3 sync" command; '
            '"--aws-use-date-modified" will permit re-syncing files if the '
            "date modified field changes."
        ),
    )
    sync_parser.add_argument(
        "--bucket-url",
        type=str,
        help="URL for an AWS S3 API compliant bucket.",
    )
    sync_parser.add_argument(
        "--discord-url",
        type=str,
        help="Discord webhook URL used to post uploaded tracks.",
    )
    sync_parser.add_argument(
        "--download-collection",
        action="store_true",
        help=(
            'Flag to trigger downloading the collection of "--import-user" '
            "from the Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--download-exclude-dirs",
        type=_convert_to_paths,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "List of paths to exclude when downloading tracks from the "
            "Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--download-include-dirs",
        type=_convert_to_paths,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "List of paths to include when downloading tracks from the "
            "Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--download-music",
        action="store_true",
        help="Flag to trigger downloading tracks from the Beatcloud.",
    )
    sync_parser.add_argument(
        "--download-spotify-playlist",
        type=str,
        help="Playlist name containing tracks to download from the Beatcloud.",
    )
    sync_parser.add_argument(
        "--dryrun",
        action="store_true",
        help=(
            'Show result of "--upload-music" or "--download-music" commands '
            "without actually running them."
        ),
    )
    sync_parser.add_argument(
        "--import-user",
        type=str,
        help='"--user" whose "--collection-path" you\'re downloading.',
    )
    sync_parser.add_argument(
        "--upload-collection",
        action="store_true",
        help=(
            'Flag to trigger uploading the collection of "--import_user" from '
            "the Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--upload-exclude-dirs",
        type=_convert_to_paths,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "List of paths to exclude when uploading tracks to the Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--upload-include-dirs",
        type=_convert_to_paths,
        nargs="+",
        action=NonEmptyListElementAction,
        help=(
            "List of paths to include when uploading tracks to the Beatcloud."
        ),
    )
    sync_parser.add_argument(
        "--upload-music",
        action="store_true",
        help="Flag to trigger uploading tracks to the Beatcloud.",
    )
    sync_parser.add_argument(
        "--usb-path",
        type=_convert_to_paths,
        help=(
            "Path to a drive containing completely and exclusively your set of"
            " audio files."
        ),
    )
    sync_parser.add_argument(
        "--user",
        type=str,
        help=(
            "Username of the current user.\nIf left empty, your operating "
            "system username will be used.\nMake sure you set this manually to"
            " a consistent value so you don't create duplicate track "
            'collections in the Beatcloud and on your "--usb-path".'
        ),
    )

    ###########################################################################
    # Sub-command for the utils package.
    ###########################################################################
    utils_parser = subparsers.add_parser(
        name="utils",
        help=(
            "Utilities that don't fit into any of the other packages.\n  - "
            "comparing tracks located in a list of Spotify playlists and/or a "
            "list of local paths to tracks in the Beatcloud to determine if "
            "you have redundancies\n  - downloading audio files from a URL "
            "containing embedded audio (e.g. Soundcloud)\n  - normalizing the "
            "peak amplitude of audio files in a list of directories\n  - "
            "processing a recording file using track data from a Spotify "
            "playlist"
        ),
        formatter_class=RawTextHelpFormatter,
    )
    utils_parser.add_argument(
        "--audio-bitrate",
        type=str,
        help='Bitrate used to save files output by "--process-recording"',
    )
    utils_parser.add_argument(
        "--audio-destination",
        type=_convert_to_paths,
        help="Location to download audio file(s) to.",
    )
    utils_parser.add_argument(
        "--audio-format",
        type=str,
        help='File format to save files output by "--process-recording"',
    )
    utils_parser.add_argument(
        "--audio-headroom",
        type=float,
        help="Amount of headroom in decibels to leave when normalizing audio.",
    )
    utils_parser.add_argument(
        "--check-tracks",
        action="store_true",
        help=(
            "Flag to trigger checking for track overlap between the Beatcloud "
            'and "--local-dirs" and / or "--check-tracks-spotify-playlists".'
        ),
    )
    utils_parser.add_argument(
        "--check-tracks-fuzz-ratio",
        type=int,
        help=(
            "Minimum similarity to indicate overlap between Beatcloud and "
            "Spotify / local tracks."
        ),
    )
    utils_parser.add_argument(
        "--check-tracks-spotify-playlists",
        type=str,
        nargs="+",
        help="List of Spotify playlist names to check against the Beatcloud.",
    )
    utils_parser.add_argument(
        "--local-dirs",
        type=_convert_to_paths,
        nargs="+",
        action=NonEmptyListElementAction,
        help="List of local directories to check against the Beatcloud.",
    )
    utils_parser.add_argument(
        "--normalize-audio",
        action="store_true",
        help='Flag to trigger normalizing audio files at "--local-dirs".',
    )
    utils_parser.add_argument(
        "--process-recording",
        action="store_true",
        help=(
            "Flag to trigger processing an audio recording using a Spotify "
            "playlist."
        ),
    )
    utils_parser.add_argument(
        "--recording-file",
        type=_convert_to_paths,
        help='Audio recording to pair with "--recording-playlist".',
    )
    utils_parser.add_argument(
        "--recording-playlist",
        type=str,
        help='Spotify playlist to pair with "--recording-file".',
    )
    utils_parser.add_argument(
        "--trim-initial-silence",
        type=_parse_trim_initial_silence,
        default=0,
        help=(
            'Milliseconds of initial silence to trim off "--recording-file". '
            "Can also be a negative integer to prepend silence. Can also be "
            '"auto" or "smart" for automatic silence detection or a '
            "home-brewed algorithm for finding the optimal offset."
        ),
    )
    utils_parser.add_argument(
        "--url-download",
        type=str,
        help="URL to download audio file(s) from.",
    )

    return parser


class NonEmptyListElementAction(Action):
    """This Action implementation permits overriding list defaults.

    Some configuration options, like UPLOAD_EXCLUDE_DIRS, may be set to some
    sensible default in config.yaml. Because of this users will be unable to
    run "--upload-music" in conjunction with "--download-include-dirs" without
    having to first make an edit to their config.yaml (because the
    include/exclude options are mutually exclusive).
    """

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: List[str],
        option_string: Optional[str] = None,
    ):
        """Filter list-type arguments for empty strings.

        Args:
            parser: The ArgumentParser object which contains this action.
            namespace: The Namespace object returned by parse_args().
            values: The associated command-line arguments.
            option_string: The option string used to invoke this action.
        """
        values = values or []
        dest = getattr(namespace, self.dest) or []
        dest.extend(filter(None, values))
        setattr(namespace, self.dest, dest)


def _convert_to_paths(paths: Union[str, List[str]]) -> Union[Path, List[Path]]:
    """Convert CLI argument from string to pathlib.Path.

    Args:
        paths: String(s) representing path(s).

    Returns:
        Path or list of Paths.
    """
    if isinstance(paths, List):
        return list(map(Path, filter(None, paths)))

    return Path(paths) if paths else ""


def _parse_json(_json: str) -> Dict:
    """Parses a JSON string and returns a dict.

    Args:
        _json: String representing JSON.

    Raises:
        Exception: JSON string must be valid JSON.

    Returns:
        Dictionary.
    """
    try:
        return json.loads(_json)
    except Exception as exc:
        raise ValueError(
            f'Unable to parse JSON type argument "{_json}": {exc}'
        ) from Exception


def _parse_trim_initial_silence(
    arg: str,
) -> Union[int, Literal["auto", "smart"]]:
    if arg in {"auto", "smart"}:
        return arg

    try:
        arg = int(arg)
    except Exception as exc:
        raise ValueError(
            '--trim-initial-silence must be either "auto", "smart", or an integer.'
        ) from exc

    return arg

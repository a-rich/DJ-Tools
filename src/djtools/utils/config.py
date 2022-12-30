"""This module is responsible for validating "config.json" and handling the
parsing of command-line arguments which, if provided, override the respective
values of "config.json"; In addition, it will update "registered_users.json"
with USER and USB_PATH.
"""
from argparse import ArgumentParser
import getpass
import json
import logging
import os
from traceback import format_exc


logger = logging.getLogger(__name__)


def build_config():
    """This function loads "config.json", updates it with command-line
        arguments, if any, validates the final config object, and then updates
        "registered_users.json" with USER and USB_PATH.

        Validation steps include:
            * Ensuring all required config options are present.
            * AWS_PROFILE is specified if also performing any sync operations.
            * Ensuring that include / exclude directory specifications are
                mutually exclusive for both uploading and downloading.
            * Warns if DISCORD_URL is absent.
            * Warns if "registered_users.json" is absent (if there are other
                users sharing this beatcloud instance, then this file should
                exist already).
            * Warns if the user is performing the sync operation "download_xml"
                while XML_IMPORT_USER is either empty or absent from
                "registered_users.json".

    Raises:
        FileNotFoundError: "config.json" must exist.
        Exception: "config.json" must be a proper JSON file.
        ValueError: "config.json" must have required options.
        ValueError: AWS_PROFILE must be specified if performing sync
            operations.
        KeyError: "AWS_PROFILE" must be configured.
        ValueError: include / exclude directories cannot both be specified
            simultaneously.
        ValueError: "XML_IMPORT_USER" must exist in "registered_user.json" 
            if "DOWNLOAD_XML".

    Returns:
        Config object.
    """
    # Load "config.json".
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "configs"
    ).replace(os.sep, "/")
    try:
        with open(
            os.path.join(config_dir, "config.json").replace(os.sep, "/"),
            mode="r",
            encoding="utf-8",
        ) as _file:
            config = json.load(_file)
    except:
        msg = f'Error reading "config.json": {format_exc()}'
        logger.critical(msg)
        raise Exception(msg) from Exception

    logger.info(f"Config: {config}")

    # Update config using command-line arguments.
    args = {k.upper(): v for k, v in arg_parse().items() if v}
    if args:
        logger.info(f"Args: {args}")
        config.update(args)

    # If doing any "sync" operations...
    syncing = any(
        config.get(op) for op in {
            "DOWNLOAD_XML", "DOWNLOAD_MUSIC", "UPLOAD_XML", "UPLOAD_MUSIC"
        }
    )
    if syncing or config.get("CHECK_TRACK_OVERLAP"):
        # Ensure AWS_PROFILE is set.
        if not config.get("AWS_PROFILE"):
            msg = (
                "Config must include AWS_PROFILE if performing sync operations"
            )
            logger.critical(msg)
            raise ValueError(msg)
        os.environ["AWS_PROFILE"] = config.get("AWS_PROFILE")

        # Warn user if uploading music without a Discord webhook URL to notify
        # other beatcloud users about new track.
        if config.get("UPLOAD_MUSIC") and not config.get("DISCORD_URL"):
            logger.warning(
                'DISCORD_URL is not configured...set this for "new music" '
                "discord messages!"
            )

    # Ensure include / exclude folders are not both set at the same time.
    if (
        (config.get("UPLOAD_INCLUDE_DIRS")
        and config.get("UPLOAD_EXCLUDE_DIRS"))
        or (config.get("DOWNLOAD_INCLUDE_DIRS")
        and config.get("DOWNLOAD_EXCLUDE_DIRS"))
    ):
        msg = (
            "Config must neither contain (a) both UPLOAD_INCLUDE_DIRS and "
            "UPLOAD_EXCLUDE_DIRS or (b) both DOWNLOAD_INCLUDE_DIRS and "
            "DOWNLOAD_EXCLUDE_DIRS"
        )
        logger.critical(msg)
        raise ValueError(msg)

    # Load "registered_users.json", warn if not present.
    registered_users_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "registered_users.json",
    ).replace(os.sep, "/")
    if os.path.exists(registered_users_path):
        try:
            with open(
                registered_users_path, mode="r", encoding="utf-8"
            ) as _file:
                registered_users = json.load(_file)
            logger.info(f"Registered users: {registered_users}")
        except:
            msg = f'Error reading "registered_users.json": {format_exc()}'
            logger.critical(msg)
            raise Exception(msg) from Exception
    else:
        registered_users = {}
        logger.warning("No registered users!")

    # Ensure XML_IMPORT_USER exists in "registered_users.json" if DOWNLOAD_XML.
    if (
        config.get("DOWNLOAD_XML") and (
            not config.get("XML_IMPORT_USER")
            or config.get("XML_IMPORT_USER") not in registered_users
        )
    ):
        raise ValueError(
            "Unable to import from XML of unregistered XML_IMPORT_USER "
            f'"{config.get("XML_IMPORT_USER")}"'
        )

    # If USER isn't set already, set it to the OS user.
    if not config.get("USER"):
        config["USER"] = getpass.getuser()

    # Enter USER into "registered_users.json".
    registered_users[config["USER"]] = config.get("USB_PATH", None)
    with open(registered_users_path, mode="w", encoding="utf-8") as _file:
        json.dump(registered_users, _file, indent=2)

    return config


def parse_json(_json: str):
    """Parses a JSON string and returns a JSON object.

    Args:
        _json: String representing JSON.

    Raises:
        Exception: JSON string must be valid JSON.

    Returns:
        JSON object.
    """
    try:
        return json.loads(_json)
    except Exception as exc:
        raise ValueError(
            f'Unable to parse JSON type argument "{_json}": {exc}'
        ) from Exception


def arg_parse():
    """This function parses command-line arguments, if any, and sets this
        module's logger's log level.

    Returns:
        argparse.NameSpace: command-line arguments
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--link_configs",
        type=str,
        metavar="FILE",
        help="symlink package configs to more user friendly location",
    )
    parser.add_argument(
        "--usb_path",
        type=str,
        metavar="FILE",
        help="path to USB with music and rekordbox files",
    )
    parser.add_argument(
        "--aws_profile",
        type=str,
        help="AWS config profile",
    )
    parser.add_argument(
        "--upload_include_dirs",
        type=str,
        nargs="+",
        help="folders to include when uploading to S3",
    )
    parser.add_argument(
        "--upload_exclude_dirs",
        type=str,
        nargs="+",
        help="folders to exclude when uploading to S3",
    )
    parser.add_argument(
        "--download_include_dirs",
        type=str,
        nargs="+",
        help="folders to include when downloading from S3",
    )
    parser.add_argument(
        "--download_exclude_dirs",
        type=str,
        nargs="+",
        help="folders to exclude when downloading from S3",
    )
    parser.add_argument(
        "--aws_use_date_modified",
        action="store_true",
        help=(
            'drop --size-only flag for "aws s3 sync" command; '
            '"--aws_use_date_modified" will permit re-downloading/'
            "re-uploading files if for e.g. their ID3 tags change"
        ),
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help='show result of "aws s3 sync" command without running',
    )
    parser.add_argument(
        "--xml_import_user",
        type=str,
        metavar="entry of registered_user.json",
        help="registered user whose 'rekordbox.xml' you're importing from",
    )
    parser.add_argument(
        "--xml_path",
        type=str,
        metavar="FILE",
        help='path to your "rekordbox.xml"',
    )
    parser.add_argument(
        "--user",
        type=str,
        metavar="entry of registered_user.json",
        help="user to add to registered_users.json (default is OS user)",
    )
    parser.add_argument(
        "--discord_url",
        type=str,
        help="discord webhook URL",
    )
    parser.add_argument(
        "--youtube_dl",
        action="store_true",
        help="perform track download",
    )
    parser.add_argument(
        "--youtube_dl_url",
        type=str,
        help="youtube_dl URL (soundcloud downloads)",
    )
    parser.add_argument(
        "--randomize_tracks",
        action="store_true",
        help="perform track randomization",
    )
    parser.add_argument(
        "--randomize_tracks_playlists",
        type=str,
        nargs="+",
        help="playlist name(s) to randomize tracks in",
    )
    parser.add_argument(
        "--download_music",
        action="store_true",
        help='sync remote beatcloud to "DJ Music" folder',
    )
    parser.add_argument(
        "--download_xml",
        action="store_true",
        help="sync remote XML of XML_IMPORT_USER to parent of XML_PATH",
    )
    parser.add_argument(
        "--upload_music",
        action="store_true",
        help='sync local "DJ Music" folder to the beatcloud',
    )
    parser.add_argument(
        "--upload_xml",
        action="store_true",
        help='sync local "XML_PATH" to the beatcloud',
    )
    parser.add_argument(
        "--rekordbox_playlists",
        action="store_true",
        help="perform automatic playlist creation",
    )
    parser.add_argument(
        "--rekordbox_playlists_remainder",
        type=str,
        choices=["folder", "playlist"],
        help=(
            'place remainder tracks in either an "Other" folder of playlists '
            'or a single "Other" playlist'
        ),
    )
    parser.add_argument(
        "--check_track_overlap",
        action="store_true",
        help="check Spotify playlists and local directories against beatcloud",
    )
    parser.add_argument(
        "--local_check_dirs",
        type=str,
        nargs="+",
        help=(
            'local directory name(s) (under "DJ Music") to check against '
            "beatcloud"
        ),
    )
    parser.add_argument(
        "--spotify_check_playlists",
        type=str,
        nargs="+",
        help="playlist name(s) to check against beatcloud",
    )
    parser.add_argument(
        "--check_track_overlap_fuzz_ratio",
        type=int,
        help=(
            "minimum Levenshtein similarity to indicate potential overlap "
            "between Spotify / local and beatcloud tracks"
        ),
    )
    parser.add_argument(
        "--spotify_client_id",
        type=str,
        help="Spotify API client ID",
    )
    parser.add_argument(
        "--spotify_client_secret",
        type=str,
        help="Spotify API client secret",
    )
    parser.add_argument(
        "--spotify_redirect_uri",
        type=str,
        help="Spotify API redirect URI",
    )
    parser.add_argument(
        "--spotify_username",
        type=str,
        help="Spotify user to maintain auto-playlists for",
    )
    parser.add_argument(
        "--auto_playlist_update",
        action="store_true",
        help="update auto-playlists",
    )
    parser.add_argument(
        "--auto_playlist_subreddits",
        type=parse_json,
        help=(
            "list of subreddits to generate playlists from; dicts with "
            '"name", "type", "period", and "limit" keys'
        ),
    )
    parser.add_argument(
        "--auto_playlist_fuzz_ratio",
        type=int,
        help="minimum Levenshtein similarity to add track to playlist",
    )
    parser.add_argument(
        "--auto_playlist_subreddit_limit",
        type=int,
        help="maximum number of subreddit posts to get",
    )
    parser.add_argument(
        "--reddit_client_id",
        type=str,
        help="Reddit API client ID",
    )
    parser.add_argument(
        "--reddit_client_secret",
        type=str,
        help="Reddit API client secret",
    )
    parser.add_argument(
        "--reddit_user_agent",
        type=str,
        help="Reddit API user agent",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="logging verbosity",
    )
    parser.add_argument(
        "--log_level",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        help="logger level",
    )
    args = parser.parse_args()

    if args.log_level:
        logger.setLevel(args.log_level)

    if args.link_configs:
        args.link_configs = args.link_configs.rstrip("/")
        if os.path.exists(args.link_configs):
            msg = (
                f"{args.link_configs} must be a directory that does not "
                "already exist"
            )
            logger.error(msg)
            raise ValueError(msg)
        if not os.path.exists(os.path.dirname(args.link_configs)):
            msg = (
                f"{os.path.dirname(args.link_configs)} must be a directory "
                "that already exists"
            )
            logger.error(msg)
            raise ValueError(msg)

        package_root = os.path.dirname(os.path.dirname(__file__))
        configs_dir = os.path.join(package_root, "configs").replace(os.sep, "/")
        os.symlink(configs_dir, args.link_configs, target_is_directory=True)

    return vars(args)

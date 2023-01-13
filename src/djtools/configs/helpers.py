"""This module is responible for building this library's configuration objects
using config.yaml. If command-line arguments are provided, this module
overrides the corresponding configuration options with these arguments.
"""
import argparse
from argparse import ArgumentParser
import logging
import os
from typing import Any, Dict, Union

import yaml

from djtools.configs.config import BaseConfig
from djtools.rekordbox.config import RekordboxConfig
from djtools.spotify.config import SpotifyConfig
from djtools.sync.config import SyncConfig
from djtools.utils.config import UtilsConfig
from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)

pkg_cfg = {
    "configs": BaseConfig,
    "rekordbox": RekordboxConfig,
    "spotify": SpotifyConfig,
    "sync": SyncConfig,
    "utils": UtilsConfig,
}


def arg_parse() -> argparse.Namespace:
    """This function parses command-line arguments.

    It also sets the log level and symlinks a user-provided directory to the
    library's configs folder via the --link-configs argument.

    Returns:
        argparse.NameSpace: Command-line arguments.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--auto-playlist-default-limit",
        type=int,
        help="Default number of tracks for a Spotify auto-playlist",
    )
    parser.add_argument(
        "--auto-playlist-default-period",
        type=str,
        help="Default Subreddit time filter for a Spotify auto-playlist",
    )
    parser.add_argument(
        "--auto-playlist-default-type",
        type=str,
        help="Default Subreddit post filter for a Spotify auto-playlist",
    )
    parser.add_argument(
        "--auto-playlist-fuzz-ratio",
        type=int,
        help="Minimum similarity to add track to an auto-playlist",
    )
    parser.add_argument(
        "--auto-playlist-post-limit",
        type=int,
        help="Maximum Subreddit posts to query for each auto-playlist",
    )
    parser.add_argument(
        "--auto-playlist-subreddits",
        type=parse_yaml,
        help=(
            "List of Subreddits configs to generate playlists from; YAML "
            'strings with "name", "type", "period", and "limit" keys'
        ),
    )
    parser.add_argument(
        "--auto-playlist-update",
        action="store_true",
        help="Trigger updating auto-playlists",
    )
    parser.add_argument(
        "--aws-profile",
        type=str,
        help="AWS config profile",
    )
    parser.add_argument(
        "--aws-use-date-modified",
        action="store_true",
        help=(
            'Drop --size-only flag for "aws s3 sync" command; '
            '"--aws-use-date-modified" will permit re-downloading/'
            "re-uploading files if the date modified field changes"
        ),
    )
    parser.add_argument(
        "--check-tracks",
        action="store_true",
        help=(
            "Trigger checking for track overlap between the Beatcloud and"
            "CHECK_TRACKS_LOCAL_DIRS and / or CHECK_TRACKS_SPOTIFY_PLAYLISTS"
        ),
    )
    parser.add_argument(
        "--check-tracks-fuzz-ratio",
        type=int,
        help=(
            "Minimum similarity to indicate overlap between Beatcloud and "
            "Spotify / local tracks"
        ),
    )
    parser.add_argument(
        "--check-tracks-local-dirs",
        type=str,
        nargs="+",
        help="List of local directories to check against the Beatcloud",
    )
    parser.add_argument(
        "--check-tracks-spotify-playlists",
        type=str,
        nargs="+",
        help="List of Spotify playlist names to check against the Beatcloud",
    )
    parser.add_argument(
        "--copy-playlists",
        type=str,
        nargs="+",
        help="List of Rekordbox playlists to copy audio files from",
    )
    parser.add_argument(
        "--copy-playlists-destination",
        type=str,
        help="Location to copy Rekordbox playlists' audio files to",
    )
    parser.add_argument(
        "--discord-url",
        type=str,
        help="Discord webhook URL",
    )
    parser.add_argument(
        "--download-exclude-dirs",
        type=str,
        nargs="+",
        help="Paths to exclude when downloading from the Beatcloud",
    )
    parser.add_argument(
        "--download-include-dirs",
        type=str,
        nargs="+",
        help="Paths to include when downloading from the Beatcloud",
    )
    parser.add_argument(
        "--download-music",
        action="store_true",
        help="Trigger downloading new tracks from the Beatcloud",
    )
    parser.add_argument(
        "--download-spotify",
        type=str,
        help="Playlist name containing tracks to download from the Beatcloud",
    )
    parser.add_argument(
        "--download-xml",
        action="store_true",
        help="Trigger downloading the XML of IMPORT_USER from the Beatcloud",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help='Show result of "aws s3 sync" command without running it',
    )
    parser.add_argument(
        "--import-user",
        type=str,
        metavar="Entry of registered_user.yaml",
        help="Registered USER whose XML_PATH you're downloading",
    )
    parser.add_argument(
        "--link-configs",
        type=str,
        help="Location to symlink library configuration files to",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logger level",
    )
    parser.add_argument(
        "--playlist-from-upload",
        action="store_true",
        help=(
            "Trigger creating a Spotify playlist using the Discord webhook "
            "output of a music upload"
        ),
    )
    parser.add_argument(
        "--pure-genre-playlists",
        type=str,
        nargs="+",
        help='List of genre tag substrings to create "pure" playlists for',
    )
    parser.add_argument(
        "--randomize-playlists",
        type=str,
        nargs="+",
        help="List of Rekordbox playlist names to randomize tracks in",
    )
    parser.add_argument(
        "--reddit-client-id",
        type=str,
        help="Reddit API client ID",
    )
    parser.add_argument(
        "--reddit-client-secret",
        type=str,
        help="Reddit API client secret",
    )
    parser.add_argument(
        "--reddit-user-agent",
        type=str,
        help="Reddit API user agent",
    )
    parser.add_argument(
        "--rekordbox-playlists",
        action="store_true",
        help="Trigger automatic Rekordbox playlist creation",
    )
    parser.add_argument(
        "--rekordbox-playlists-remainder",
        type=str,
        choices=["folder", "playlist"],
        help=(
            'Place remainder tracks in either an "Other" folder of playlists '
            'or a single "Other" playlist'
        ),
    )
    parser.add_argument(
        "--spotify-client-id",
        type=str,
        help="Spotify API client ID",
    )
    parser.add_argument(
        "--spotify-client-secret",
        type=str,
        help="Spotify API client secret",
    )
    parser.add_argument(
        "--spotify-redirect-uri",
        type=str,
        help="Spotify API redirect URI",
    )
    parser.add_argument(
        "--spotify-username",
        type=str,
        help="Spotify user to maintain auto-playlists for",
    )
    parser.add_argument(
        "--upload-exclude-dirs",
        type=str,
        nargs="+",
        help="List of paths to exclude when uploading to the Beatcloud",
    )
    parser.add_argument(
        "--upload-include-dirs",
        type=str,
        nargs="+",
        help="List of paths to include when uploading to the Beatcloud",
    )
    parser.add_argument(
        "--upload-music",
        action="store_true",
        help="Trigger uploading new tracks from the Beatcloud",
    )
    parser.add_argument(
        "--upload-xml",
        action="store_true",
        help="Trigger uploading the XML of IMPORT_USER from the Beatcloud",
    )
    parser.add_argument(
        "--url-download",
        type=str,
        help="URL to download audio file(s) from",
    )
    parser.add_argument(
        "--url-download-destination",
        type=str,
        help="Location to download audio file(s) to",
    )
    parser.add_argument(
        "--usb-path",
        type=str,
        help="Path to a drive with audio files",
    )
    parser.add_argument(
        "--user",
        type=str,
        metavar="Entry of registered_user.yaml",
        help="Entry in registered_users.yaml which maps to your USB_PATH",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="Logging verbosity",
    )
    parser.add_argument(
        "--xml-path",
        type=str,
        help='Path to your exported Rekordbox XML database',
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
        parent_dir = os.path.dirname(args.link_configs)
        if not os.path.exists(parent_dir):
            make_dirs(parent_dir)

        package_root = os.path.dirname(os.path.dirname(__file__))
        configs_dir = os.path.join(package_root, "configs").replace(os.sep, "/")
        os.symlink(configs_dir, args.link_configs, target_is_directory=True)

    return vars(args)


def build_config():
    """This function loads configurations for the library.
    
    Configurations are loaded from config.yaml. If command-line arguments are
    provided, these override the configuration options set in config.yaml.

    Raises:
        RuntimeError: config.yaml must be a valid YAML.

    Returns:
        Global configuration object.
    """
    # Load "config.yaml".
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "configs"
    ).replace(os.sep, "/")
    config_file = os.path.join(config_dir, "config.yaml").replace(os.sep, "/")
    if os.path.exists(config_file):
        try:
            with open(config_file, mode="r", encoding="utf-8") as _file:
                config = yaml.load(_file, Loader=yaml.FullLoader) or {}
        except Exception as exc:
            msg = f'Error reading "config.yaml": {exc}'
            logger.critical(msg)
            raise RuntimeError(msg) from Exception
    else:
        config = {}
        base_config_fields = BaseConfig.__fields__
        initial_config = {
            pkg: {
                k: v.default for k, v in cfg.__fields__.items()
                if pkg == "configs" or k not in base_config_fields
            }
            for pkg, cfg in pkg_cfg.items()
        }
        with open(config_file, mode="w", encoding="utf-8") as _file:
            yaml.dump(initial_config, _file)

    # Update config using command-line arguments.
    args = {k.upper(): v for k, v in arg_parse().items() if v}
    if args:
        logger.info(f"Args: {args}")
        args_set = set(args)
        for pkg, cfg_class in pkg_cfg.items():
            args_intersection = set(cfg_class.__fields__).intersection(args_set)
            if args_intersection:
                args_subset = {
                    k: v for k, v in args.items() if k in args_intersection
                }
                if pkg in config:
                    config[pkg].update(args_subset)
                else:
                    config[pkg] = args_subset

    # Instantiate Pydantic models.
    base_cfg_options = config["configs"] if config else {}
    configs = {
        pkg: cfg(**{**base_cfg_options, **config.get(pkg, {})})
        for pkg, cfg in pkg_cfg.items() if pkg != "configs"
    }
    joined_config = BaseConfig(
        **base_cfg_options,
        **{
            k: v for cfg in configs.values()
            for k, v in filter_dict(cfg).items()
        }
    )

    return joined_config


def filter_dict(
    sub_config: Union[RekordboxConfig, SpotifyConfig, SyncConfig, UtilsConfig],
) -> Dict[Any, Any]:
    """Filters out the superclass key: value pairs of a subclass.

    Args:
        sub_config: Instance of any subclass of BaseConfig.

    Returns:
        Dictionary containing just the keys unique to `sub_config`.
    """
    super_keys = set(BaseConfig.__fields__)
    return {
        k: v for k, v in sub_config.dict().items() if k not in super_keys
    }


def parse_yaml(_yaml: str):
    """Parses a YAML string and returns a YAML object.

    Args:
        _yaml: String representing YAML.

    Raises:
        Exception: YAML string must be valid YAML.

    Returns:
        YAML object.
    """
    try:
        return yaml.safe_load(_yaml)
    except Exception as exc:
        raise ValueError(
            f'Unable to parse YAML type argument "{_yaml}": {exc}'
        ) from Exception

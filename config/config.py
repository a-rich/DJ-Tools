"""This module is responsible for validating 'config.json' which is used by
this library and handling the parsing of command-line arguments which, if
provided, override the respective values of 'config.json'; In addition, it will
update 'registered_users.json' with the current user's username and USB_PATH.
"""
from argparse import ArgumentParser
import json
import logging
import os
from traceback import format_exc


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('parser')

# This is the template for 'config.json' specifying the required and necessary
# config options as well as their value types.
CONFIG_TEMPLATE = {
    "USB_PATH": "",
    "AWS_PROFILE": "",
    "UPLOAD_INCLUDE_DIRS": [],
    "UPLOAD_EXCLUDE_DIRS": [],
    "DOWNLOAD_INCLUDE_DIRS": [],
    "DOWNLOAD_EXCLUDE_DIRS": [],
    "AWS_USE_DATE_MODIFIED": False,
    "XML_IMPORT_USER": "",
    "XML_PATH": "",
    "USER": "",
    "LOG_DIR": "",
    "DISCORD_URL": "",
    "YOUTUBE_DL": False,
    "YOUTUBE_DL_URL": "",
    "RANDOMIZE_TRACKS": False,
    "RANDOMIZE_TRACKS_PLAYLISTS": "",
    "RANDOMIZE_TRACKS_TAG": "",
    "SYNC_OPERATIONS": [],
    "GET_GENRES": False,
    "GENRE_EXCLUDE_DIRS": [],
    "GENRE_TAG_DELIMITER": "",
    "GENERATE_GENRE_PLAYLISTS": False,
    "GENERATE_GENRE_PLAYLISTS_REMAINDER": "",
    "SPOTIFY_CHECK_PLAYLISTS": False,
    "SPOTIFY_PLAYLISTS_CHECK": [],
    "SPOTIFY_PLAYLISTS_CHECK_FUZZ_RATIO": 80,
    "SPOTIFY_CLIENT_ID": "",
    "SPOTIFY_CLIENT_SECRET": "",
    "SPOTIFY_REDIRECT_URI": "",
    "SPOTIFY_USERNAME": "",
    "AUTO_PLAYLIST_UPDATE": False,
    "AUTO_PLAYLIST_SUBREDDITS": [],
    "AUTO_PLAYLIST_TRACK_LIMIT": 50,
    "AUTO_PLAYLIST_TOP_PERIOD": "",
    "AUTO_PLAYLIST_LEVENSHTEIN_SIMILARITY": 80,
    "REDDIT_CLIENT_ID": "",
    "REDDIT_CLIENT_SECRET": "",
    "REDDIT_USER_AGENT": "",
    "VERBOSITY": 0,
    "LOG_LEVEL": "INFO"
}


def arg_parse():
    """This function parses command-line arguments, if any, and sets this
    module's logger's log level.

    Returns:
        argparse.NameSpace: command-line arguments
    """
    p = ArgumentParser()
    p.add_argument('--usb_path', type=str, metavar='FILE',
            help='path to USB with music and rekordbox files')
    p.add_argument('--aws_profile', type=str,
            help='AWS config profile')
    p.add_argument('--upload_include_dirs', type=str, nargs='+',
            help='folders to include when uploading to S3')
    p.add_argument('--upload_exclude_dirs', type=str, nargs='+',
            help='folders to exclude when uploading to S3')
    p.add_argument('--download_include_dirs', type=str, nargs='+',
            help='folders to include when downloading from S3')
    p.add_argument('--download_exclude_dirs', type=str, nargs='+',
            help='folders to exclude when downloading from S3')
    p.add_argument('--aws_use_date_modified', action='store_true',
            help='drop --size-only flag for `aws s3 sync` command; ' \
                 '--aws_use_date_modified will permit re-downloading/' \
                 're-uploading files if their ID3 tags change')
    p.add_argument('--xml_import_user', type=str,
            metavar='entry of registered_user.json',
            help="registered user whose 'rekordbox.xml' you're importing from")
    p.add_argument('--xml_path', type=str, metavar='FILE',
            help='path to "rekordbox.xml" you are importing from')
    p.add_argument('--user', type=str, metavar='entry of registered_user.json',
            help='user to add to registered_users.json (default is OS user)')
    p.add_argument('--log_dir', type=str, metavar='DIRECTORY',
            help='directory where log files are stored')
    p.add_argument('--discord_url', type=str,
            help='discord webhook URL')
    p.add_argument('--youtube_dl', action='store_true',
            help='perform track download')
    p.add_argument('--youtube_dl_url', type=str,
            help='youtube_dl URL (soundcloud / youtube downloads)')
    p.add_argument('--randomize_tracks', action='store_true',
            help='perform track randomization')
    p.add_argument('--randomize_tracks_playlists', type=str, nargs='+',
            help='playlist name(s) to randomize tracks in')
    p.add_argument('--randomize_tracks_tag', type=str,
            choices=['track_num'],
            help='ID3 tag to use for encoding randomization')
    p.add_argument('--sync_operations', nargs='+',
            choices=['upload_music', 'upload_xml', 'download_music',
                     'download_xml'],
            help='DJ Tools sync operations to perform')
    p.add_argument('--get_genres', action='store_true',
            help='perform genre analysis')
    p.add_argument('--genre_exclude_dirs', type=str, nargs='+',
            help='paths to exclude from tracks during genre analysis')
    p.add_argument('--genre_tag_delimiter', type=str,
            help='expected delimiter for "genre" tags')
    p.add_argument('--generate_genre_playlists', action='store_true',
            help='perform automatic genre playlist creation')
    p.add_argument('--generate_genre_playlists_remainder', type=str,
            choices=['folder', 'playlist'],
            help='place remainder tracks in either a folder of genre ' \
                 'playlists or a single "Other" playlist')
    p.add_argument('--spotify_check_playlists', action='store_true',
            help='check Spotify playlists against beatcloud')
    p.add_argument('--spotify_playlists_check', type=str, nargs='+',
            help='playlist name(s) to check against beatcloud')
    p.add_argument('--spotify_playlists_check_fuzz_ratio', type=int,
            help='playlist name(s) to check against beatcloud')
    p.add_argument('--spotify_client_id', type=str,
            help='Spotify API client ID')
    p.add_argument('--spotify_client_secret', type=str,
            help='Spotify API client secret')
    p.add_argument('--spotify_redirect_uri', type=str,
            help='Spotify API redirect URI')
    p.add_argument('--spotify_username', type=str,
            help='Spotify user to maintain auto-playlists for')
    p.add_argument('--auto_playlist_update', action='store_true',
            help='update auto-playlists')
    p.add_argument('--auto_playlist_subreddits', type=str, nargs='+',
            help='subreddits to generate playlists from')
    p.add_argument('--auto_playlist_track_limit', type=int,
            help='maximum number of tracks in a playlist')
    p.add_argument('--auto_playlist_top_period', type=str,
            choices=['all', 'day', 'hour', 'month', 'week', 'year'],
            help='"top" period to consider when updating playlists')
    p.add_argument('--auto_playlist_levenshtein_similarity', type=int,
            help='minimum Levenshtein similarity to add track to playlist')
    p.add_argument('--reddit_client_id', type=str,
            help='Reddit API client ID')
    p.add_argument('--reddit_client_secret', type=str,
            help='Reddit API client secret')
    p.add_argument('--reddit_user_agent', type=str,
            help='Reddit API user agent')
    p.add_argument('--verbosity', '-v', action='count', default=0,
            help='logging verbosity')
    p.add_argument('--log_level',
            choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
            help='default logger level')
    args = p.parse_args()

    if args.log_level:
        logger.setLevel(args.log_level)

    return args


def update_config(args):
    """This function loads 'config.json', updates it with command-line
    arguments, if any, validates the final config object, and then updates
    'registered_users.json' with the current user's username and USB_PATH.
    Validation steps include:
        * ensuring all required config options are present
        * AWS_PROFILE is specified if also performing any sync operations
        * ensuring that include / exclude directory specifications are mutually
          exclusive for both uploading and downloading
        * warns if DISCORD_URL is absent
        * warns if 'registered_users.json' is absent (if there are other users
          sharing this beatcloud instances, then this file should exist already)
        * warns if the user is performing the sync operation 'download_xml'
          while XML_IMPORT_USER is either empty or absent from
          'registered_users.json'

    Args:
        args (argparser.NameSpace): command-line arguments 

    Raises:
        FileNotFoundError: 'config.json' must exist
        Exception: 'config.json' must be a proper JSON file
        ValueError: 'config.json' must have required options
        ValueError: AWS_PROFILE must be specified if performing sync operations
        ValueError: include / exclude directories cannot both be specified
                    simultaneously

    Returns:
        dict: config object
    """
    try:
        config_file = os.path.join('config', 'config.json')
        config = json.load(open(config_file, 'r'))
        logger.info(f'Config: {config}')
    except FileNotFoundError:
        msg = '"config.json" file not found.'
        logger.critical(msg)
        raise FileNotFoundError(msg)
    except:
        msg = f'Error reading "config.json": {format_exc()}'
        logger.critical(msg)
        raise Exception(msg)

    args = {k.upper(): v for k, v in vars(args).items() if v}
    if args:
        logger.info(f'Args: {args}')
        config.update(args)

    missing_config_keys = [k for k in CONFIG_TEMPLATE if k not in config]
    if missing_config_keys:
        msg = f'Config does not contain required keys: {missing_config_keys}'
        logger.critical(msg)
        raise ValueError(msg)
    
    if config['SYNC_OPERATIONS'] and not config.get('AWS_PROFILE'):
        msg = 'Config must include AWS_PROFILE if performing sync operations'
        logger.critical(msg)
        raise ValueError(msg)
    os.environ['AWS_PROFILE'] = config['AWS_PROFILE']

    if (config['UPLOAD_INCLUDE_DIRS'] and config['UPLOAD_EXCLUDE_DIRS']) \
            or (config['DOWNLOAD_INCLUDE_DIRS'] and 
                config['DOWNLOAD_EXCLUDE_DIRS']):
        msg = 'Config must neither contain (a) both UPLOAD_INCLUDE_DIRS and ' \
              'UPLOAD_EXCLUDE_DIRS or (b) both DOWNLOAD_INCLUDE_DIRS and' \
              'DOWNLOAD_EXCLUDE_DIRS'
        logger.critical(msg)
        raise ValueError(msg)

    if not config['DISCORD_URL']:
        logger.warning('DISCORD_URL is not configured...set this for ' \
                       '"new music" discord messages!')

    registered_users_path = os.path.join('config', 'registered_users.json')
    if os.path.exists(registered_users_path):
        registered_users = json.load(open(registered_users_path))
        logger.info(f'Registered users: {registered_users}')
    else:
        logger.warning('No registered users, "git pull" to ensure you are ' \
                       'up-to-date!')
        registered_users = {}

    if 'download_xml' in config['SYNC_OPERATIONS'] and (
            not config['XML_IMPORT_USER']
            or config['XML_IMPORT_USER'] not in registered_users):
        logger.warning('Unable to import from XML of unregistered user ' \
                       f'"{config["XML_IMPORT_USER"]}"')
        config['SYNC_OPERATIONS'].remove('download_xml')

    if not config.get('USER'):
        config['USER'] = os.environ.get('USER')

    os.makedirs(config['LOG_DIR'], exist_ok=True)
    registered_users[config['USER']] = config['USB_PATH']
    json.dump(registered_users, open(registered_users_path, 'w'))

    return config

"""This module is responsible for validating 'config.json' and handling the
parsing of command-line arguments which, if provided, override the respective
values of 'config.json'; In addition, it will update 'registered_users.json'
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
    """This function loads 'config.json', updates it with command-line
    arguments, if any, validates the final config object, and then updates
    'registered_users.json' with USER and USB_PATH.
    Validation steps include:
        * ensuring all required config options are present
        * AWS_PROFILE is specified if also performing any sync operations
        * ensuring that include / exclude directory specifications are mutually
          exclusive for both uploading and downloading
        * warns if DISCORD_URL is absent
        * warns if 'registered_users.json' is absent (if there are other users
          sharing this beatcloud instance, then this file should exist already)
        * warns if the user is performing the sync operation 'download_xml'
          while XML_IMPORT_USER is either empty or absent from
          'registered_users.json'

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
    # load 'config.json'
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              'configs')
    try:
        with open(os.path.join(config_dir, 'config.json'), 'r',
                  encoding='utf-8') as _file:
            config = json.load(_file)
    except FileNotFoundError:
        with open(os.path.join(config_dir, 'config_template.json'), 'r',
                  encoding='utf-8') as _file:
            config = json.load(_file)
        with open(os.path.join(config_dir, 'config.json'), 'w',
                  encoding='utf-8') as _file:
            json.dump(config, _file, indent=2)
    except:
        msg = f'Error reading "config.json": {format_exc()}'
        logger.critical(msg)
        raise Exception(msg) from Exception

    logger.info(f'Config: {config}')

    # update config using command-line arguments
    args = {k.upper(): v for k, v in arg_parse().items() if v}
    if args:
        logger.info(f'Args: {args}')
        config.update(args)

    # identify any required keys that are absent from the config
    with open(os.path.join(config_dir, 'config_template.json'), 'r',
                encoding='utf-8') as _file:
        config_template = json.load(_file)
    missing_config_keys = [k for k in config_template if k not in config]
    if missing_config_keys:
        msg = f'Config does not contain required keys: {missing_config_keys}'
        logger.critical(msg)
        raise ValueError(msg)

    # if doing SYNC_OPERATIONS...
    if config['SYNC_OPERATIONS']:
        # ensure AWS_PROFILE is set
        if not config.get('AWS_PROFILE'):
            msg = 'Config must include AWS_PROFILE if performing sync ' \
                  'operations'
            logger.critical(msg)
            raise ValueError(msg)

        # warn user if uploading music without a Discord webhook URL to notify
        # other beatcloud users about new tracks
        if 'upload_music' in config['SYNC_OPERATIONS'] \
                and not config['DISCORD_URL']:
            logger.warning('DISCORD_URL is not configured...set this for ' \
                        '"new music" discord messages!')

    os.environ['AWS_PROFILE'] = config['AWS_PROFILE']

    # ensure include / exclude folders are not both set at the same time
    if (config['UPLOAD_INCLUDE_DIRS'] and config['UPLOAD_EXCLUDE_DIRS']) \
            or (config['DOWNLOAD_INCLUDE_DIRS'] and
                config['DOWNLOAD_EXCLUDE_DIRS']):
        msg = 'Config must neither contain (a) both UPLOAD_INCLUDE_DIRS and ' \
              'UPLOAD_EXCLUDE_DIRS or (b) both DOWNLOAD_INCLUDE_DIRS and' \
              'DOWNLOAD_EXCLUDE_DIRS'
        logger.critical(msg)
        raise ValueError(msg)

    # load 'registered_users.json', warn if not present
    registered_users_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'configs',
            'registered_users.json')
    if os.path.exists(registered_users_path):
        registered_users = json.load(open(registered_users_path,
                                          encoding='utf-8'))
        logger.info(f'Registered users: {registered_users}')
    else:
        logger.warning('No registered users, "git pull" to ensure you are ' \
                       'up-to-date!')
        registered_users = {}

    # if downloading another user's XML and that user doesn't have an entry in
    # 'registered_users.json', display a warning and remove 'download_xml' from
    # SYNC_OPERATIONS
    if 'download_xml' in config['SYNC_OPERATIONS'] and (
            not config['XML_IMPORT_USER']
            or config['XML_IMPORT_USER'] not in registered_users):
        logger.warning('Unable to import from XML of unregistered user ' \
                       f'"{config["XML_IMPORT_USER"]}"')
        config['SYNC_OPERATIONS'].remove('download_xml')

    # if USER isn't set already, set it to the OS user
    if not config.get('USER'):
        config['USER'] = getpass.getuser()

    # enter USER into 'registered_users.json'
    registered_users[config['USER']] = config['USB_PATH']
    with open(registered_users_path, 'w', encoding='utf-8') as _file:
        json.dump(registered_users, _file, indent=2)

    return config


def arg_parse():
    """This function parses command-line arguments, if any, and sets this
    module's logger's log level.

    Returns:
        argparse.NameSpace: command-line arguments
    """
    parser = ArgumentParser()
    parser.add_argument('--link_configs', type=str, metavar='FILE',
            help='symlink package configs to more user friendly location')
    parser.add_argument('--usb_path', type=str, metavar='FILE',
            help='path to USB with music and rekordbox files')
    parser.add_argument('--aws_profile', type=str,
            help='AWS config profile')
    parser.add_argument('--upload_include_dirs', type=str, nargs='+',
            help='folders to include when uploading to S3')
    parser.add_argument('--upload_exclude_dirs', type=str, nargs='+',
            help='folders to exclude when uploading to S3')
    parser.add_argument('--download_include_dirs', type=str, nargs='+',
            help='folders to include when downloading from S3')
    parser.add_argument('--download_exclude_dirs', type=str, nargs='+',
            help='folders to exclude when downloading from S3')
    parser.add_argument('--aws_use_date_modified', action='store_true',
            help='drop --size-only flag for `aws s3 sync` command; ' \
                 '--aws_use_date_modified will permit re-downloading/' \
                 're-uploading files if their ID3 tags change')
    parser.add_argument('--xml_import_user', type=str,
            metavar='entry of registered_user.json',
            help="registered user whose 'rekordbox.xml' you're importing from")
    parser.add_argument('--xml_path', type=str, metavar='FILE',
            help='path to your "rekordbox.xml"')
    parser.add_argument('--user', type=str,
            metavar='entry of registered_user.json',
            help='user to add to registered_users.json (default is OS user)')
    parser.add_argument('--discord_url', type=str,
            help='discord webhook URL')
    parser.add_argument('--youtube_dl', action='store_true',
            help='perform track download')
    parser.add_argument('--youtube_dl_url', type=str,
            help='youtube_dl URL (soundcloud downloads)')
    parser.add_argument('--randomize_tracks', action='store_true',
            help='perform track randomization')
    parser.add_argument('--randomize_tracks_playlists', type=str, nargs='+',
            help='playlist name(s) to randomize tracks in')
    parser.add_argument('--randomize_tracks_tag', type=str,
            choices=['track_num'],
            help='ID3 tag to use for encoding randomization')
    parser.add_argument('--sync_operations', nargs='+',
            choices=['upload_music', 'upload_xml', 'download_music',
                     'download_xml'],
            help='DJ Tools sync operations to perform')
    parser.add_argument('--get_genres', action='store_true',
            help='perform genre analysis')
    parser.add_argument('--genre_exclude_dirs', type=str, nargs='+',
            help='paths to exclude from tracks during genre analysis')
    parser.add_argument('--genre_tag_delimiter', type=str,
            help='delimiter for "genre" tags')
    parser.add_argument('--generate_genre_playlists', action='store_true',
            help='perform automatic genre playlist creation')
    parser.add_argument('--generate_genre_playlists_remainder', type=str,
            choices=['folder', 'playlist'],
            help='place remainder tracks in either an "Other" folder of ' \
                 'genre playlists or a single "Other" playlist')
    parser.add_argument('--spotify_check_playlists', action='store_true',
            help='check Spotify playlists against beatcloud')
    parser.add_argument('--spotify_playlists_check', type=str, nargs='+',
            help='playlist name(s) to check against beatcloud')
    parser.add_argument('--spotify_playlists_check_fuzz_ratio', type=int,
            help='minimum Levenshtein similarity to indicate potential ' \
                 'overlap between Spotify and beatcloud tracks')
    parser.add_argument('--spotify_client_id', type=str,
            help='Spotify API client ID')
    parser.add_argument('--spotify_client_secret', type=str,
            help='Spotify API client secret')
    parser.add_argument('--spotify_redirect_uri', type=str,
            help='Spotify API redirect URI')
    parser.add_argument('--spotify_username', type=str,
            help='Spotify user to maintain auto-playlists for')
    parser.add_argument('--auto_playlist_update', action='store_true',
            help='update auto-playlists')
    parser.add_argument('--auto_playlist_subreddits', type=str, nargs='+',
            help='subreddits to generate playlists from')
    parser.add_argument('--auto_playlist_track_limit', type=int,
            help='maximum number of tracks in a playlist')
    parser.add_argument('--auto_playlist_top_period', type=str,
            choices=['all', 'day', 'hour', 'month', 'week', 'year'],
            help='"top" period to consider when updating playlists')
    parser.add_argument('--auto_playlist_fuzz_ratio', type=int,
            help='minimum Levenshtein similarity to add track to playlist')
    parser.add_argument('--reddit_client_id', type=str,
            help='Reddit API client ID')
    parser.add_argument('--reddit_client_secret', type=str,
            help='Reddit API client secret')
    parser.add_argument('--reddit_user_agent', type=str,
            help='Reddit API user agent')
    parser.add_argument('--verbosity', '-v', action='count', default=0,
            help='logging verbosity')
    parser.add_argument('--log_level',
            choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
            help='logger level')
    args = parser.parse_args()

    if args.link_configs:
        os.symlink(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'configs'),
                   args.link_configs,
                   target_is_directory=True)

    if args.log_level:
        logger.setLevel(args.log_level)

    return vars(args)

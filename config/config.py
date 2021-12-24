from argparse import ArgumentParser
import json
import logging
import os
from traceback import format_exc

from dateutil.parser import parse


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('parser')

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
    "DISCORD_CONTENT_SIZE_LIMIT": 2000,
    "YOUTUBE_DL_URL": "",
    "RANDOMIZE_TRACKS_PLAYLISTS": "",
    "RANDOMIZE_TRACKS_TAG": "track_num",
    "SYNC_OPERATIONS": [],
    "GET_GENRES": False,
    "GENRE_TAG_DELIMITER": "",
    "GENRE_EXCLUDE_DIRS": [],
    "SPOTIFY_PLAYLISTS_CHECK": [],
    "SPOTIFY_PLAYLISTS_CHECK_FUZZ_RATIO": 72,
    "SPOTIFY_CLIENT_ID": "",
    "SPOTIFY_CLIENT_SECRET": "",
    "SPOTIFY_REDIRECT_URI": "",
    "VERBOSITY": 0
}


def date_checker(date):
    try:
        return parse(date)
    except ValueError:
        raise ValueError(f'{date} is not a valid datetime')


def arg_parse():
    p = ArgumentParser()
    p.add_argument('--usb_path', type=str, metavar='FILE',
            help='path to USB with music and rekordbox files')
    p.add_argument('--aws_profile', type=str,
            help='AWS configuration profile')
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
    p.add_argument('--discord_content_size_limit', type=int,
            help='webhook content size limit')
    p.add_argument('--youtube_dl_url', type=str,
            help='youtube_dl URL (soundcloud / youtube downloads)')
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
    p.add_argument('--genre_tag_delimiter', type=str,
            help='expected delimiter for "genre" tags')
    p.add_argument('--genre_exclude_dirs', type=str, nargs='+',
            help='paths to exclude from tracks during genre analysis')
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
    try:
        config_file = os.path.join('config', 'config.json')
        config = json.load(open(config_file, 'r'))
        logger.info(f'Read config: {config}')
    except FileNotFoundError:
        msg = 'No "config.json" file found.'
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

    for key in CONFIG_TEMPLATE:
        missing_config_keys = []
        if key not in config:
            missing_config_keys.append(key)

    if missing_config_keys:
        msg = f'Config does not contain required keys: {missing_config_keys}'
        logger.critical(msg)
        raise ValueError(msg)

    if not config.get('AWS_PROFILE'):
        msg = 'config must include AWS_PROFILE'
        logger.critical(msg)
        raise ValueError(msg)

    os.environ['AWS_PROFILE'] = config['AWS_PROFILE']

    if (config['UPLOAD_INCLUDE_DIRS'] and config['UPLOAD_EXCLUDE_DIRS']) \
            or (config['DOWNLOAD_INCLUDE_DIRS'] and 
                config['DOWNLOAD_EXCLUDE_DIRS']):
        msg = 'config must not contain either (a) both UPLOAD_INCLUDE_DIRS ' \
              'and UPLOAD_EXCLUDE_DIRS or (b) both DOWNLOAD_INCLUDE_DIRS ' \
              'and DOWNLOAD_EXCLUDE_DIRS'
        logger.critical(msg)
        raise ValueError(msg)

    if not config['DISCORD_URL']:
        logger.warning('DISCORD_URL is not configured...set this for ' \
                       '"new music" discord messages!')

    if os.path.exists('registered_users.json'):
        registered_users = json.load(open('registered_users.json', 'r'))
        logger.info(f'Registered users: {registered_users}')
    else:
        logger.warning(f'No registered users, "git pull" to ensure you are ' \
                       'up-to-date!')
        registered_users = {}

    if 'download_xml' in config['SYNC_OPERATIONS'] and (
            not config['XML_IMPORT_USER']
            or config['XML_IMPORT_USER'] not in registered_users):
        logger.warning(f'Unable to import from XML of unregistered user ' \
                       f'"{config["XML_IMPORT_USER"]}"')
        config['SYNC_OPERATIONS'].remove('download_xml')

    if not config.get('USER'):
        config['USER'] = os.environ.get('USER')

    os.makedirs(config['LOG_DIR'], exist_ok=True)
    registered_users[config['USER']] = config['USB_PATH']
    json.dump(registered_users, open('registered_users.json', 'w'))

    return config

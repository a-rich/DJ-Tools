"""This module is used to download tracks from 'YOUTUBE_DL_URL'. For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""
import logging
import os
import re

import youtube_dl as ytdl

from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)


def youtube_dl(config):
    """Downloads music files from a provided URL using the youtube-dl package.

    Args:
        config (dict): configuration object

    Raises:
        FileNotFoundError: 'USB_PATH' must exist
    """
    if not os.path.exists(config['USB_PATH']):
        raise FileNotFoundError(f'{config["USB_PATH"]} does not exist!')

    dest_path = os.path.join(config['USB_PATH'], 'DJ Music', 'New Music',
                             '').replace(os.sep, '/')
    if not os.path.exists(dest_path):
        make_dirs(dest_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': dest_path + '%(title)s.%(ext)s'
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        logger.info(f'Downloading {config["YOUTUBE_DL_URL"]} to {dest_path}')
        ydl.download([config['YOUTUBE_DL_URL']])

    for _file in os.listdir(dest_path):
        os.rename(os.path.join(dest_path, _file).replace(os.sep, '/'),
                  os.path.join(dest_path, fix_up(_file)).replace(os.sep, '/'))


def fix_up(_file):
    """Removes digits appended to file name by youtube-dl.

    Args:
        _file (str): music file name

    Returns:
        str: cleaned up music file name
    """
    name, ext = os.path.splitext(_file)
    stripped = ''.join(re.split(r"(\-\d{1,}\.)", name)[:1] + ['.'] +
        re.split(r"(\-\d{1,}\.)", name)[2:])
    name = ' - '.join(stripped.split(' - ')[-1::-1])

    return name + ext

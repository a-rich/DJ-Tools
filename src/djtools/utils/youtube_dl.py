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
        KeyError: 'USB_PATH' must be configured
        KeyError: 'YOUTUBE_DL_URL' must be configured
        FileNotFoundError: 'USB_PATH' must exist
    """
    try:
        usb_path = config['USB_PATH']
    except KeyError:
        raise KeyError('Using the youtube_dl module requires the config ' \
                       'option USB_PATH') from KeyError
    
    try:
        youtube_dl_url = config['YOUTUBE_DL_URL']
    except KeyError:
        raise KeyError('Using the youtube_dl module requires the config ' \
                       'option YOUTUBE_DL_URL') from KeyError

    if not os.path.exists(usb_path):
        raise FileNotFoundError(f'{usb_path} does not exist!')

    dest_path = os.path.join(usb_path, 'DJ Music', 'New Music',
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
        logger.info(f'Downloading {youtube_dl_url} to {dest_path}')
        ydl.download([youtube_dl_url])

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

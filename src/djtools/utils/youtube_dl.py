"""This module is used to download tracks from 'YOUTUBE_DL_URL'. For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""
import logging
import os
import re

import youtube_dl as ytdl


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

    dest_path = os.path.join(config['USB_PATH'], 'DJ Music', 'New Music', '')
    if not os.path.exists(dest_path):
        if os.name == 'nt':
            cwd = os.getcwd()
            path_parts = dest_path.split(os.path.sep)
            root = path_parts[0]
            path_parts = path_parts[1:]
            os.chdir(root)
            for part in path_parts:
                os.makedirs(part, exist_ok=True)
                os.chdir(part)
            os.chdir(cwd)
        else:
            os.makedirs(dest_path, exist_ok=True)

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
        os.rename(os.path.join(dest_path, _file),
                  os.path.join(dest_path, fix_up(_file)))


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

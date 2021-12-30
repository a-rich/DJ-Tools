"""This module is used to download tracks from 'YOUTUBE_DL_URL'. For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""
import logging
import os
import re

import youtube_dl as ytdl


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('youtube_dl')


def youtube_dl(config):
    """Downloads music files from a provided URL using the youtube-dl package.

    Args:
        config (dict): configuration object

    Raises:
        FileNotFoundError: 'USB_PATH' must exist
    """
    if not os.path.exists(config['USB_PATH']):
        raise FileNotFoundError(f'{config["USB_PATH"]} does not exist!')

    DEST_PATH = os.path.join(config['USB_PATH'], 'DJ Music', 'New Music', '')
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': DEST_PATH + '%(title)s.%(ext)s'
    }
    with ytdl.YoutubeDL(ydl_opts) as ydl:
        logger.info(f'Downloading {config["YOUTUBE_DL_URL"]} to {DEST_PATH}')
        ydl.download([config['YOUTUBE_DL_URL']])
    
    for _file in os.listdir(DEST_PATH):
        os.rename(os.path.join(DEST_PATH, _file),
                  os.path.join(DEST_PATH, fix_up(_file)))


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

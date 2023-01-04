"""This module is used to download tracks from "YOUTUBE_DL_URL". For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""
import logging
import os
import re

import youtube_dl as ytdl

from djtools.utils.config import UtilsConfig
from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)


def fix_up(_file: str) -> str:
    """Removes digits appended to file name by youtube-dl.

    Args:
        _file: Music file name.

    Returns:
        Cleaned up music file name.
    """
    _, ext = os.path.splitext(_file)
    exp = fr"(\-\d{{1,}}(?={ext}))"
    stripped = os.path.splitext(re.split(exp, _file)[0])[0]
    name = " - ".join(stripped.split(" - ")[-1::-1])

    return name + ext


def youtube_dl(config: UtilsConfig):
    """Downloads music files from a provided URL using the youtube-dl package.

    Args:
        config: Configuration object.
    """
    dl_loc = config.YOUTUBE_DL_LOCATION or "."
    dl_loc = os.path.join(dl_loc, "").replace(os.sep, "/")
    make_dirs(dl_loc)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        "outtmpl": dl_loc + "%(title)s.%(ext)s"
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading {config.YOUTUBE_DL_URL} to {dl_loc}")
        ydl.download([config.YOUTUBE_DL_URL])

    for _file in os.listdir(dl_loc):
        os.rename(
            os.path.join(dl_loc, _file).replace(os.sep, "/"),
            os.path.join(dl_loc, fix_up(_file)).replace(os.sep, "/"),
        )

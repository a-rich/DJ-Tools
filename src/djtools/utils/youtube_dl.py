"""This module is used to download tracks from "YOUTUBE_DL_URL". For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""
import logging
import os
import re
from typing import Dict, List, Union

import youtube_dl as ytdl

from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)


def youtube_dl(config: Dict[str, Union[List, Dict, str, bool, int, float]]):
    """Downloads music files from a provided URL using the youtube-dl package.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "USB_PATH" must be configured.
        KeyError: "YOUTUBE_DL_URL" must be configured.
        FileNotFoundError: "USB_PATH" must exist.
    """
    try:
        youtube_dl_url = config["YOUTUBE_DL_URL"]
    except KeyError:
        raise KeyError(
            "Using the youtube_dl module requires the config option "
            "YOUTUBE_DL_URL"
        ) from KeyError

    dl_loc = config.get("YOUTUBE_DL_LOCATION") or "."
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
        logger.info(f"Downloading {youtube_dl_url} to {dl_loc}")
        ydl.download([youtube_dl_url])

    for _file in os.listdir(dl_loc):
        os.rename(
            os.path.join(dl_loc, _file).replace(os.sep, "/"),
            os.path.join(dl_loc, fix_up(_file)).replace(os.sep, "/"),
        )


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

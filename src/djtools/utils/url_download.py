"""This module is used to download tracks from "URL_DOWNLOAD". For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""

import logging
from pathlib import Path
import re

import youtube_dl as ytdl

from djtools.configs.config import BaseConfig
from djtools.utils.helpers import make_path


logger = logging.getLogger(__name__)


@make_path
def fix_up(_file: Path) -> Path:
    """Removes digits appended to file name by youtube-dl.

    Args:
        _file: Music file name.

    Returns:
        Cleaned up music file name.
    """
    ext = _file.suffix
    exp = rf"(\-\d{{1,}}(?={ext}))"
    stripped = Path(re.split(exp, _file.as_posix())[0]).stem
    name = Path(" - ".join(stripped.split(" - ")[-1::-1]))

    return name.with_suffix(ext)


def url_download(config: BaseConfig):
    """Downloads music files from a provided URL using the youtube-dl package.

    Args:
        config: Configuration object.
    """
    dl_loc = config.AUDIO_DESTINATION or Path(".")
    dl_loc.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config.AUDIO_FORMAT,
                "preferredquality": config.AUDIO_BITRATE,
            }
        ],
        "outtmpl": (dl_loc / "%(title)s.tmp").as_posix(),
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading {config.URL_DOWNLOAD} to {dl_loc}")
        ydl.download([config.URL_DOWNLOAD])

    for _file in dl_loc.iterdir():
        (dl_loc / _file).rename(dl_loc / fix_up(_file))

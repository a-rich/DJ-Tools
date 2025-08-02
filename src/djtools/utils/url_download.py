"""This module is used to download tracks from "url_download". For example, a
Soundcloud playlist can be made and the URL of that playlist can be provided to
download all those tracks and rename them to cleanup the digits appended to the
files by the youtube-dl package.
"""

import logging
import re
from pathlib import Path
from typing import Type

import youtube_dl as ytdl

from djtools.utils.helpers import make_path


logger = logging.getLogger(__name__)
BaseConfig = Type["BaseConfig"]


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
    dl_loc = config.utils.audio_destination or Path(".")
    dl_loc.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config.utils.audio_format.value,
                "preferredquality": config.utils.audio_bitrate,
            }
        ],
        "outtmpl": (dl_loc / "%(title)s.tmp").as_posix(),
    }

    with ytdl.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading {config.utils.url_download} to {dl_loc}")
        ydl.download([config.utils.url_download])

    for _file in dl_loc.iterdir():
        (dl_loc / _file).rename(dl_loc / fix_up(_file))

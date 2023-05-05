"""This module contains helper functions used by the "sync_operations" module.
Helper functions include formatting "aws s3 sync" commands, formatting the
output of "aws s3 sync" commands, posting uploaded tracks to Discord, and
modifying IMPORT_USER's XML to point to tracks located at "USB_PATH".
"""
from datetime import datetime, timedelta
from itertools import groupby
import logging
from pathlib import Path
from subprocess import Popen, PIPE, CalledProcessError
from typing import Optional
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup
import requests

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


def parse_sync_command(
    _cmd: str, config: BaseConfig, upload: Optional[bool] = False,
) -> str:
    """Appends flags to "aws s3 sync" command. If "*_INCLUDE_DIRS" is
        specified, all directories are ignored except those specified. If
        "*_EXCLUDE_DIRS" is specified, all directories are included except
        those specified. Only one of these can be specified at once. If
        "AWS_USE_DATE_MODIFIED", then tracks will be
        re-downloaded / re-uploaded if their date modified at the source is
        after that of the destination.

    Args:
        _cmd: Partial "aws s3 sync" command.
        config: Configuration object.
        upload: Whether uploading or downloading.

    Returns:
        Fully constructed "aws s3 sync" command.
    """
    if (
        (upload and config.UPLOAD_INCLUDE_DIRS)
        or (not upload and config.DOWNLOAD_INCLUDE_DIRS)
    ):
        _cmd.extend(["--exclude", "*"])
        directories = map(
            Path,
            getattr(config, f'{"UP" if upload else "DOWN"}LOAD_INCLUDE_DIRS'),
        )
        for _dir in directories:
            path = Path(_dir.stem)
            ext = _dir.suffix
            if not ext:
                path = _dir / "*"
            else:
                path = _dir.parent / path.with_suffix(ext)
            _cmd.extend(["--include", path.as_posix()])
    if (
        (upload and config.UPLOAD_EXCLUDE_DIRS)
        or (not upload and config.DOWNLOAD_EXCLUDE_DIRS)
    ):
        _cmd.extend(["--include", "*"])
        directories = map(
            Path,
            getattr(config, f'{"UP" if upload else "DOWN"}LOAD_EXCLUDE_DIRS'),
        )
        for _dir in directories:
            path = Path(_dir.stem)
            ext = _dir.suffix
            if not ext:
                path = _dir / "*"
            else:
                path = _dir.parent / path.with_suffix(ext)
            _cmd.extend(["--exclude", path.as_posix()])
    if not config.AWS_USE_DATE_MODIFIED:
        _cmd.append("--size-only")
    if config.DRYRUN:
        _cmd.append("--dryrun")
    logger.info(" ".join(_cmd))

    return _cmd


def rewrite_xml(config: BaseConfig, loc_prefix: str = "file://localhost"):
    """This function modifies the "Location" field of track tags in a
        downloaded Rekordbox XML replacing the "USB_PATH" written by
        "IMPORT_USER" with the "USB_PATH" in "config.yaml".

    Args:
        config: Configuration object.
        loc_prefix: Prefix of the `Location` field.
    """
    xml_path = (
        Path(config.XML_PATH).parent / f"{config.IMPORT_USER}_rekordbox.xml"
    )
    music_path = "DJ Music"
    usb_path = config.USB_PATH.as_posix().strip("/")

    with open(xml_path, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            loc = unquote(track["Location"])
            common_path = f"{music_path}/{loc.split(music_path + '/')[-1]}"
            loc = f"{loc_prefix}/{usb_path}/{common_path}"
            track["Location"] = quote(loc)


    with open(xml_path, mode="wb", encoding=soup.orignal_encoding) as _file:
        _file.write(soup.prettify("utf-8"))


def run_sync(_cmd: str) -> str:
    """Runs subprocess for "aws s3 sync" command. Output is collected and
        formatted such that uploaded tracks are grouped by their directories.

    Args:
        _cmd: "aws s3 sync" command.

    Raises:
        CalledProcessError: raised if "aws s3 sync" command fails.

    Returns:
        Formatted list of uploaded tracks; tracks are grouped by directory.
    """
    tracks = []
    try:
        with Popen(_cmd, stdout=PIPE, universal_newlines=True) as proc:
            while True:
                line = proc.stdout.readline()
                if line == "" and proc.poll() is not None:
                    break
                if "upload: " in line:
                    print(line.strip(), flush=True)
                    tracks.append(
                        line.strip().split(
                            " to s3://dj.beatcloud.com/dj/music/"
                        )[-1]
                    )
                else:
                    print(
                        f"{line.strip()}                                  "
                        "                        ",
                        end="\r", flush=True
                    )

            proc.stdout.close()
            return_code = proc.wait()
        if return_code:
            raise CalledProcessError(return_code, " ".join(_cmd))
    except Exception as exc:
        msg = f"Failure while syncing: {exc}"
        logger.critical(msg)
        raise Exception(msg) from exc

    new_music = ""
    if tracks:
        logger.info(
            f'Successfully {"down" if "s3://" in _cmd[3] else "up"}loaded the '
            "following tracks:"
        )
    for group_id, group in groupby(
        sorted(tracks, key=lambda x: "/".join(x.split("/")[:-1])),
        key=lambda x: "/".join(x.split("/")[:-1]),
    ):
        group = sorted(group)
        new_music += f"{group_id}: {len(group)}\n"
        for track in group:
            track = track.split("/")[-1]
            new_music += f"\t{track}\n"
    if new_music:
        logger.info(new_music)

    return new_music


def upload_log(config: BaseConfig, log_file: Path):
    """This function uploads "log_file" to the "USER" logs folder in S3. It
        then deletes all files created more than one day ago.

    Args:
        config: Configuration object.
        log_file: Path to log file.
    """
    if not config.AWS_PROFILE:
        logger.warning(
            "Logs cannot be backed up without specifying the config option "
            "AWS_PROFILE"
        )
        return

    dst = f"s3://dj.beatcloud.com/dj/logs/{config.USER}/{log_file.name}"
    cmd = f"aws s3 cp {log_file.as_posix()} {dst}"
    logger.info(cmd)
    with Popen(cmd, shell=True) as proc:
        proc.wait()

    now = datetime.now()
    one_day = timedelta(days=1)
    for _file in log_file.parent.rglob("*"):
        if _file.name == "empty.txt":
            continue
        if _file.lstat().st_mtime < (now - one_day).timestamp():
            _file.unlink()


def webhook(
    url: str, content_size_limit: int = 2000, content: Optional[str] = None
):
    """Post track list of newly uploaded tracks to Discord channel associated
        with "url". Track list is split across multiple messages if the
        character limit exceed "content_size_limit".

    Args:
        url (str): Discord URL for webhook.
        content_size_limit: Character limit for Discord message; if content is
            larger, then multiple messages are sent.
        content: Uploaded tracks (if any).
    """
    if not content:
        logger.info("There's no content")
        return

    batch = content[:content_size_limit]
    remainder = content[content_size_limit:]
    while batch:
        index = content_size_limit - 1
        while True:
            if index == 0:
                index = content_size_limit
                break
            try:
                if batch[index] == "\n":
                    break
            except IndexError:
                break
            index -= 1
        remainder = batch[index+1:] + remainder
        batch = batch[:index+1]

        if batch:
            requests.post(url, json={"content": batch}, timeout=10)
            batch = remainder[:content_size_limit]
            remainder = remainder[content_size_limit:]

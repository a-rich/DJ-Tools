"""This module contains helper functions used by the "sync_operations" module.
Helper functions include formatting "aws s3 sync" commands, formatting the
output of "aws s3 sync" commands, posting uploaded tracks to Discord, and
modifying XML_IMPORT_USER's XML to point to tracks located at "USB_PATH".
"""
from itertools import groupby
import json
import logging
import os
from subprocess import Popen, PIPE, CalledProcessError
from typing import Dict, List, Optional, Union

from bs4 import BeautifulSoup
import requests


logger = logging.getLogger(__name__)


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
                    print(f"{line.strip()}                                  " \
                          "                        ", end="\r", flush=True)

            proc.stdout.close()
            return_code = proc.wait()
        if return_code:
            raise CalledProcessError(return_code, " ".join(_cmd))
    except Exception as exc:
        msg = f"Failure while syncing: {exc}"
        logger.critical(msg)
        raise Exception(msg)

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


def parse_sync_command(
    _cmd: str,
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
    upload: Optional[bool] = False,
) -> str:
    """Appends flags to "aws s3 sync" command. If "*_INCLUDE_DIRS" is
        specified, all directories are ignored except those specified. If
        "*_EXCLUDE_DIRS" is specified, all directories are included except
        those specified. Only one of these can be specified at once. If
        "AWS_USE_DATE_MODIFIED", then tracks will be redownloaded / reuploaded
        if their date modified at the source is after that of the destination.

    Args:
        _cmd: Partial "aws s3 sync" command.
        config: Configuration object.
        upload: Whether uploading or downloading.
    
    Raises:
        ValueError: include / exclude directories cannot both be specified
            simultaneously.

    Returns:
        Fully constructed "aws s3 sync" command.
    """
    if (
        (config.get("UPLOAD_INCLUDE_DIRS")
        and config.get("UPLOAD_EXCLUDE_DIRS"))
        or (config.get("DOWNLOAD_INCLUDE_DIRS")
        and config.get("DOWNLOAD_EXCLUDE_DIRS"))
    ):
        msg = (
            "Config must neither contain (a) both UPLOAD_INCLUDE_DIRS and "
            "UPLOAD_EXCLUDE_DIRS or (b) both DOWNLOAD_INCLUDE_DIRS and "
            "DOWNLOAD_EXCLUDE_DIRS"
        )
        logger.critical(msg)
        raise ValueError(msg)
    if (
        config.get("UPLOAD_INCLUDE_DIRS")
        or config.get("DOWNLOAD_INCLUDE_DIRS")
    ):
        _cmd.extend(["--exclude", "*"])
        for _dir in config.get(
            f'{"UP" if upload else "DOWN"}LOAD_INCLUDE_DIRS', []
        ):
            _cmd.extend(
                [
                    "--include",
                    os.path.join(_dir, "*").replace(os.sep, "/"),
                ]
            )
    if (
        config.get("UPLOAD_EXCLUDE_DIRS")
        or config.get("DOWNLOAD_EXCLUDE_DIRS")
    ):
        _cmd.extend(["--include", "*"])
        for _dir in config.get(
            f'{"UP" if upload else "DOWN"}LOAD_EXCLUDE_DIRS', []
        ):
            _cmd.extend(
                [
                    "--exclude",
                    os.path.join(_dir, "*").replace(os.sep, "/"),
                ]
            )
    if not config.get("AWS_USE_DATE_MODIFIED"):
        _cmd.append("--size-only")
    if config.get("DRYRUN"):
        _cmd.append("--dryrun")
    logger.info(" ".join(_cmd))

    return _cmd


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
            requests.post(url, json={"content": batch})
            batch = remainder[:content_size_limit]
            remainder = remainder[content_size_limit:]


def rewrite_xml(config: Dict[str, Union[List, Dict, str, bool, int, float]]):
    """This function modifies the "Location" field of track tags in a
        downloaded Rekordbox XML replacing the "USB_PATH" written by
        "XML_IMPORT_USER" with the "USB_PATH" in "config.json".

    Args:
        config: Configuration object.

    Raises:
        KeyError: "XML_PATH" must be configured.
    """
    xml_path = config.get("XML_PATH")
    if not xml_path:
        raise ValueError(
            "Using the sync_operations module's download_xml function "
            "requires the config option XML_PATH"
        )

    registered_users_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "registered_users.json",
    ).replace(os.sep, "/")

    with open(registered_users_path, mode="r", encoding="utf-8") as _file:
        registered_users = json.load(_file)
        src = registered_users[config["XML_IMPORT_USER"]].strip("/")
        dst = registered_users[config["USER"]].strip("/")

    xml_path = os.path.join(
        os.path.dirname(xml_path),
        f'{config["XML_IMPORT_USER"]}_rekordbox.xml',
    ).replace(os.sep, "/")

    with open(xml_path, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            track["Location"] = track["Location"].replace(src, dst)

    with open(xml_path, mode="wb", encoding=soup.orignal_encoding) as _file:
        _file.write(soup.prettify("utf-8"))

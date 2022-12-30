"""This module contains top-level helper functions.
    * upload_logs: Writes a log file to the logs directory of S3.
"""
from datetime import datetime, timedelta
from glob import glob
import logging
import os
from os import name as os_name
from typing import Any, Callable, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


def upload_log(
    config: Dict[str, Union[List, Dict, str, bool, int, float]], log_file: str
):
    """This function uploads "log_file" to the "USER" logs folder in S3. It
        then deletes all files created more than one day ago.

    Args:
        config: Configuration object.
        log_file: Path to log file.
    """
    if not config.get("AWS_PROFILE"):
        logger.warning(
            "Logs cannot be backed up without specifying the config option "
            "AWS_PROFILE"
        )
        return

    dst = (
        "s3://dj.beatcloud.com/dj/logs/"
        f'{config["USER"]}/{os.path.basename(log_file)}'
    )
    cmd = f"aws s3 cp {log_file} {dst}"
    logger.info(cmd)
    os.system(cmd)

    now = datetime.now()
    one_day = timedelta(days=1)
    for _file in glob(f"{os.path.dirname(log_file)}/*"):
        if os.path.basename(_file) == "empty.txt":
            continue
        if os.path.getmtime(_file) < (now - one_day).timestamp():
            os.remove(_file)


def make_dirs(path: str):
    """This function performs operating system agnostic directory creation.

    Args:
        path: Directory path.
    """
    if os_name == "nt":
        cwd = os.getcwd()
        path_parts = path.split(os.sep)
        if path_parts and not path_parts[0]:
            path_parts[0] = "/"
        root = path_parts[0]
        path_parts = path_parts[1:]
        os.chdir(root)
        for part in path_parts:
            os.makedirs(part, exist_ok=True)
            os.chdir(part)
        os.chdir(cwd)
    else:
        os.makedirs(path, exist_ok=True)


def catch(
    func: Callable,
    *args,
    handle: Optional[Callable] = lambda e: None,
    **kwargs,
):  
    """This function permits one-line try/except logic for comprehensions.

    Args:
        func: Function to try.
        handle: Handler function.

    Returns:
        Callable to handle exception.
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        return handle(exc)


def raise_(exc: Exception):
    """This function permits raising exceptions in unnamed functions.

    Args:
        exc: Arbitrary exception.

    Raises:
        Arbitrary exception.
    """
    raise exc

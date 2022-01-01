"""This module contains top-level helper functions.
    * upload_logs: writes a log file to the logs directory of S3
"""
import logging
import os


logger = logging.getLogger(__name__)


def upload_log(config, log_file):
    """This function uploads 'log_file' to the 'USER' logs folder in S3.

    Args:
        config (dict): configuration object
        log_file (str): path to log file
    """
    dst = 's3://dj.beatcloud.com/dj/logs/' \
          f'{config["USER"]}/{os.path.basename(log_file)}'
    cmd = f'aws s3 cp {log_file} {dst}'
    logger.info(cmd)
    os.system(cmd)

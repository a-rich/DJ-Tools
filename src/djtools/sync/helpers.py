"""This module contains helper functions used by the 'sync_operations' module.
Helper functions include formatting 'aws s3 sync' commands, formatting the
output of 'aws s3 sync' commands, posting uploaded tracks to Discord, and
modifying XML_IMPORT_USER's XML to point to tracks located at 'USB_PATH'.
"""
from itertools import groupby
import json
import logging
import os
from subprocess import Popen, PIPE, CalledProcessError
from traceback import format_exc

from bs4 import BeautifulSoup
import requests


logger = logging.getLogger(__name__)


def run_sync(_cmd):
    """Runs subprocess for 'aws s3 sync' command. Output is collected and
    formatted such that uploaded tracks are grouped by their directories.

    Args:
        _cmd (str): 'aws s3 sync' command

    Raises:
        CalledProcessError: raised if 'aws s3 sync' command fails

    Returns:
        str: formatted list of uploaded tracks; tracks are grouped by directory
    """
    tracks = []
    try:
        with Popen(_cmd, stdout=PIPE, universal_newlines=True) as proc:
            while True:
                line = proc.stdout.readline()
                if line == '' and proc.poll() is not None:
                    break
                if 'upload: ' in line:
                    print(line.strip(), flush=True)
                    tracks.append(line.strip().split(
                            ' to s3://dj.beatcloud.com/dj/music/')[-1])
                else:
                    print(f'{line.strip()}                                  ' \
                          '                        ', end='\r', flush=True)

            proc.stdout.close()
            return_code = proc.wait()
        if return_code:
            raise CalledProcessError(return_code, _cmd)
    except AttributeError:
        logger.error('No new track')
    except Exception:
        logger.error(f'Failure while syncing: {format_exc()}')

    new_music = ''
    if tracks:
        logger.info(f'Successfully {"down" if "s3://" in _cmd[3] else "up"}' \
                    'loaded the following tracks:')
    for group_id, group in groupby(sorted(tracks,
            key=lambda x: '/'.join(x.split('/')[:-1])),
            key=lambda x: '/'.join(x.split('/')[:-1])):
        group = sorted(group)
        new_music += f'{group_id}: {len(group)}\n'
        for track in group:
            track = track.split('/')[-1]
            new_music += f'\t{track}\n'
    if new_music:
        logger.info(new_music)

    return new_music


def parse_sync_command(_cmd, config, upload=False):
    """Appends flags to 'aws s3 sync' command. If '*_INCLUDE_DIRS' is
    specified, all directories are ignored except those specified. If
    '*_EXCLUDE_DIRS' is specified, all directories are included except those
    specified. Only one of these can be specified at once. If
    'AWS_USE_DATE_MODIFIED', then tracks will be redownloaded / reuploaded if
    their date modified at the source is after that of the destination.

    Args:
        _cmd (str): partial 'aws s3 sync' command
        config (str): configuration object
        upload (bool, optional): whether uploading or downloading

    Returns:
        str: fully built 'aws s3 sync' command
    """
    if (upload and config['UPLOAD_INCLUDE_DIRS']) or \
            (not upload and config['DOWNLOAD_INCLUDE_DIRS']):
        _cmd.extend(['--exclude', '*'])
        for _dir in config[f'{"UP" if upload else "DOWN"}LOAD_INCLUDE_DIRS']:
            _cmd.extend(['--include', f'{_dir}/*'])
    if (upload and config['UPLOAD_EXCLUDE_DIRS']) or \
            (not upload and config['DOWNLOAD_EXCLUDE_DIRS']):
        _cmd.extend(['--include', '*'])
        for _dir in config[f'{"UP" if upload else "DOWN"}LOAD_EXCLUDE_DIRS']:
            _cmd.extend(['--exclude', f'{_dir}/*'])
    if not config['AWS_USE_DATE_MODIFIED']:
        _cmd.append('--size-only')

    return _cmd


def webhook(url, content=None, content_size_limit=2000):
    """Post track list of newly uploaded tracks to Discord channel associated
    with 'url'. Track list is split across multiple messages if the character
    limit exceed 'content_size_limit'.

    Args:
        url (str): Discord URL for webhook
        content (str, optional): uploaded tracks (if any)
        content_size_limit (int, optional): character limit for Discord
                                            message; if content is larger, then
                                            multiple messages are sent
    """
    if not content:
        logger.info("There's no content")
        return

    batch = content[:content_size_limit]
    remainder = content[content_size_limit:]
    while batch:
        index = content_size_limit - 1
        while True:
            try:
                if batch[index] == '\n':
                    break
            except IndexError:
                break
            index -= 1
        remainder = batch[index+1:] + remainder
        batch = batch[:index+1]

        try:
            requests.post(url, json={"content": batch})
        except Exception:
            logger.error(format_exc())

        batch = remainder[:content_size_limit]
        remainder = remainder[content_size_limit:]


def rewrite_xml(config):
    """This function modifies the 'Location' field of track tags in a
    downloaded Rekordbox XML replacing the 'USB_PATH' written by
    'XML_IMPORT_USER' with the 'USB_PATH' in 'config.json'.

    Args:
        config (dict): configuration object
    """
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           'configs', 'registered_users.json'),
              encoding='utf-8') as _file:
        registered_users = json.load(_file)
        src = registered_users[config['XML_IMPORT_USER']]
        dst = registered_users[config['USER']]

    if os.name == 'nt':
        dst = '/' + os.path.splitdrive(dst)[0] + '/'

    xml_path = os.path.join(os.path.dirname(config['XML_PATH']),
                            f'{config["XML_IMPORT_USER"]}_rekordbox.xml')
    soup = BeautifulSoup(open(xml_path, 'r', encoding='utf-8').read(), 'xml')
    for track in soup.find_all('TRACK'):
        if not track.get('Location'):
            continue
        track['Location'] = track['Location'].replace(os.path.join(src, ''),
                os.path.join(dst, ''))

    with open(xml_path, mode='wb',
              encoding=soup.orignal_encoding) as _file:
        _file.write(soup.prettify('utf-8'))

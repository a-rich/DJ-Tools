from itertools import groupby
import logging
import os
from subprocess import Popen, PIPE, CalledProcessError
from traceback import format_exc

import requests


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('sync helpers')


def run_sync(_cmd):
    tracks = []
    try:
        p = Popen(_cmd, stdout=PIPE, universal_newlines=True)

        while True:
            line = p.stdout.readline()
            if line == '' and p.poll() is not None:
                break
            if 'upload: ' in line:
                print(line.strip(), flush=True)
                tracks.append(line.strip().split(' to s3://dj.beatcloud.com/dj/music/')[-1])
            else:
                print(f'{line.strip()}                                                          ',
                        end='\r', flush=True)

        p.stdout.close()
        return_code = p.wait()
        if return_code:
            raise CalledProcessError(return_code, _cmd)
    except AttributeError:
        logger.error('No new track')
    except Exception as e:
        logger.error(f'Failure while syncing: {format_exc()}')

    new_music = ''
    if tracks:
        logger.info(f'\nSuccessfully {"down" if "s3://" in _cmd[3] else "up"}loaded the following tracks:')
    for g, group in groupby(sorted(tracks,
            key=lambda x: '/'.join(x.split('/')[:-1])),
            key=lambda x: '/'.join(x.split('/')[:-1])):
        group = sorted(group)
        new_music += f'{g}: {len(group)}\n'
        for track in group:
            x = track.split('/')[-1]
            new_music += f'\t{x}\n'
    if new_music:
        logger.info(new_music)

    return new_music


def parse_include_exclude(_cmd, config, upload=False):
    if (upload and config['UPLOAD_INCLUDE_DIRS']) or \
            (not upload and config['DOWNLOAD_INCLUDE_DIRS']):
        _cmd.extend(['--exclude', '*'])
        for x in config[f'{"UP" if upload else "DOWN"}LOAD_INCLUDE_DIRS']:
            _cmd.extend(['--include', f'{x}/*'])
    if (upload and config['UPLOAD_EXCLUDE_DIRS']) or \
            (not upload and config['DOWNLOAD_EXCLUDE_DIRS']):
        _cmd.extend(['--include', '*'])
        for x in config[f'{"UP" if upload else "DOWN"}LOAD_EXCLUDE_DIRS']:
            _cmd.extend(['--exclude', f'{x}/*'])
    if not config['AWS_USE_DATE_MODIFIED']:
        _cmd.append('--size-only')

    return _cmd


def webhook(url, content_size_limit, content=None):
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


def rewrite_xml(file_, config):
    logger.info('Syncing remote rekordbox.xml...')
    cmd = f"aws s3 cp s3://dj.beatcloud.com/dj/xml/{config['XML_IMPORT_USER']}/rekordbox.xml {file_}"
    logger.info(cmd)
    os.system(cmd)

    src = config['XML_IMPORT_USER']

    if os.name == 'posix':
        dst = config['USB_PATH']
    else:
        dst = '/' + os.path.splitdrive(config['USB_PATH'])[0] + '/'

    lines = open(file_, 'r', encoding='utf-8').readlines()
    with open(file_, 'w', encoding='utf-8') as f:
        for line in lines:
            if 'file://localhost' in line:
                line = line.replace(src,
                                    os.path.join(dst, ''))
            f.write(f"{line.strip()}\n")

from datetime import datetime
import logging
import os
from pathlib import Path

from src.sync.helpers import parse_include_exclude, rewrite_xml, run_sync, webhook


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('sync_operations')


def upload_music(config):
    glob_path = Path(os.path.join(config['USB_PATH'], 'DJ Music'))
    hidden_files = set([str(p) for p in glob_path.rglob(os.path.join('**',
                                                                     '.*.*'))])
    if hidden_files:
        logger.info(f'Removed {len(hidden_files)} files...')
        for _file in hidden_files:
            logger.info(f'\t{_file}')
            os.remove(_file)

    logger.info('Syncing local track collection...')
    cmd = ['aws', 's3', 'sync',
           f"{os.path.join(config['USB_PATH'], 'DJ Music')}",
           's3://dj.beatcloud.com/dj/music/']

    if config['DISCORD_URL']:
        webhook(config['DISCORD_URL'], config['DISCORD_CONTENT_SIZE_LIMIT'],
                content=run_sync(parse_include_exclude(cmd, config, upload=True)))
    else:
        _ = run_sync(cmd)


def upload_xml(config):
    logger.info(f"Uploading {config['USER']}'s local rekordbox.xml...")
    dst = f's3://dj.beatcloud.com/dj/xml/{config["USER"]}/'
    cmd = f'aws s3 cp {config["XML_PATH"]} {dst}'
    logger.info(cmd)
    os.system(cmd)


def download_music(config):
    glob_path = Path(os.path.join(config['USB_PATH'], 'DJ Music'))
    old = set([str(p) for p in glob_path.rglob(os.path.join('**', '*.*'))])
    logger.info(f"Found {len(old)} files")

    logger.info(f"Syncing remote track collection...")
    os.makedirs(os.path.join(config['USB_PATH'], 'DJ Music'), exist_ok=True)
    cmd = ['aws', 's3', 'sync', 's3://dj.beatcloud.com/dj/music/',
           f"{os.path.join(config['USB_PATH'], 'DJ Music')}"]
    _ = run_sync(parse_include_exclude(cmd, config))

    new = set([str(p) for p in glob_path.rglob(os.path.join('**', '*.*'))])
    difference = sorted(list(new.difference(old)),
                        key=lambda x: os.path.getmtime(x))
    if difference:
        logger.info(f"Found {len(difference)} new files")
        os.makedirs(os.path.join(config['LOG_DIR'], 'new'), exist_ok=True)
        now = datetime.now().strftime('%Y-%m-%dT%H.%M.%S')
        log_file = f"{now}.txt"
        with open(os.path.join(config['LOG_DIR'], 'new', log_file), 'w',
                  encoding='utf-8') as f:
            for x in difference:
                logger.info(f"\t{x}")
                f.write(f"{x}\n")


def download_xml(config):
    if os.name == 'nt':
        cwd = os.getcwd()
        path_parts = os.path.dirname(config['XML_PATH']).split(os.path.sep)
        root = path_parts[0]
        path_parts = path_parts[1:]
        os.chdir(root)
        for part in path_parts:
            os.makedirs(part, exist_ok=True)
            os.chdir(part)
        rewrite_xml(f'{config["XML_IMPORT_USER"]}_rekordbox.xml', config)
        os.chdir(cwd)
    else:
        xml_dir = os.path.dirname(config['XML_PATH'])
        os.makedirs(xml_dir, exist_ok=True)
        rewrite_xml(os.path.join(xml_dir,
                                 f'{config["XML_IMPORT_USER"]}_rekordbox.xml'),
                    config)


SYNC_OPERATIONS = {
    'upload_music': upload_music,
    'upload_xml': upload_xml,
    'download_music': download_music,
    'download_xml': download_xml
}

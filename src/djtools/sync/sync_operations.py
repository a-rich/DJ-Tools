"""This module is responsible for syncing tracks between 'USB_PATH' and the
beatcloud (upload and download). It also handles uploading the Rekordbox XML
located at 'XML_PATH' and downloading the Rekordbox XML uploaded to the
beatcloud by 'XML_IMPORT_USER' before modifying it to point to track locations
at 'USB_PATH'.
"""
import logging
import os
from pathlib import Path

from djtools.sync.helpers import parse_sync_command, rewrite_xml, run_sync, \
                                 webhook
from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)


def upload_music(config):
    """This function syncs tracks from 'USB_PATH' to the beatcloud.
    'AWS_USE_DATE_MODIFIED' can be used in order to reupload tracks that
    already exist in the beatcloud but have been modified since the last time
    they were uploaded (i.e. ID3 tags have been altered).

    Args:
        config (dict): configuration object

    Raises:
        KeyError: 'USB_PATH' must be configured
        FileNotFoundError: 'USB_PATH' must exist
    """
    try:
        usb_path = config['USB_PATH']
    except KeyError:
        raise KeyError('Using the upload_music mode of the sync_operations ' \
                       'module requires the config option USB_PATH') \
                from KeyError

    if not os.path.exists(usb_path):
        raise FileNotFoundError(f'USB_PATH "{usb_path}" does not exist!')

    glob_path = Path(os.path.join(usb_path,
                                  'DJ Music').replace(os.sep, '/'))
    hidden_files = {str(p) for p in glob_path.rglob(
            os.path.join('**', '.*.*').replace(os.sep, '/'))}
    if hidden_files:
        logger.info(f'Removed {len(hidden_files)} files...')
        for _file in hidden_files:
            logger.info(f'\t{_file}')
            os.remove(_file)

    logger.info('Syncing track collection...')
    src = os.path.join(usb_path, 'DJ Music').replace(os.sep, '/')
    cmd = ['aws', 's3', 'sync', src, 's3://dj.beatcloud.com/dj/music/']

    if config.get('DISCORD_URL') and not config.get('DRYRUN'):
        webhook(config['DISCORD_URL'],
                content=run_sync(parse_sync_command(cmd, config, upload=True)))
    else:
        run_sync(parse_sync_command(cmd, config, upload=True))


def upload_xml(config):
    """This function uploads 'XML_PATH' to beatcloud.

    Args:
        config (dict): configuration object

    Raises:
        KeyError: 'XML_PATH' must be configured
        FileNotFoundError: 'XML_PATH' file must exist
    """
    try:
        xml_path = config['XML_PATH']
    except KeyError:
        raise KeyError('Using the upload_xml mode of the sync_operations ' \
                       'module requires the config option XML_PATH') \
                from KeyError

    if not os.path.exists(xml_path):
        raise FileNotFoundError(f'XML_PATH "{xml_path}" does not exist!')

    logger.info(f"Uploading {config['USER']}'s rekordbox.xml...")
    dst = f's3://dj.beatcloud.com/dj/xml/{config["USER"]}/'
    cmd = f'aws s3 cp {xml_path} {dst}'
    logger.info(cmd)
    os.system(cmd)


def download_music(config):
    """This function syncs tracks from the beatcloud to 'USB_PATH'.
    'AWS_USE_DATE_MODIFIED' can be used in order to redownload tracks that
    already exist in 'USB_PATH' but have been modified since the last time they
    were downloaded (i.e. ID3 tags have been altered).

    Args:
        config (dict): configuration object

    Raises:
        KeyError: 'USB_PATH' must be configured
        FileNotFoundError: 'USB_PATH' must exist
    """
    try:
        usb_path = config['USB_PATH']
    except KeyError:
        raise KeyError('Using the download_music mode of the sync_operations ' \
                       'module requires the config option USB_PATH') \
                from KeyError
    
    if not os.path.exists(usb_path):
        raise FileNotFoundError(f'USB_PATH "{usb_path}" does not exist!')

    dest = os.path.join(usb_path, 'DJ Music').replace(os.sep, '/')
    glob_path = Path(dest)
    old = {str(p) for p in glob_path.rglob(
            os.path.join('**', '*.*').replace(os.sep, '/'))}
    logger.info(f"Found {len(old)} files")

    logger.info("Syncing remote track collection...")
    make_dirs(dest)
    cmd = ['aws', 's3', 'sync', 's3://dj.beatcloud.com/dj/music/', dest]
    run_sync(parse_sync_command(cmd, config))

    new = {str(p) for p in glob_path.rglob(
            os.path.join('**', '*.*').replace(os.sep, '/'))}
    difference = sorted(list(new.difference(old)), key=os.path.getmtime)
    if difference:
        logger.info(f"Found {len(difference)} new files")
        for diff in difference:
            logger.info(f"\t{diff}")


def download_xml(config):
    """This function downloads the beatcloud XML of 'XML_IMPORT_USER' and
    modifies the 'Location' field of all the tracks so that it points to USER's
    'USB_PATH'.

    Args:
        config (dict): configuration object

    Raises:
        KeyError: 'XML_PATH' must be configured
        FileNotFoundError: XML destination directory must exist
    """
    try:
        xml_path = config['XML_PATH']
    except KeyError:
        raise KeyError('Using the download_xml mode of the sync_operations ' \
                       'module requires the config option XML_PATH') \
                from KeyError

    logger.info('Syncing remote rekordbox.xml...')
    xml_dir = os.path.dirname(xml_path)
    make_dirs(xml_dir)
    _file = f'{config["XML_IMPORT_USER"]}_rekordbox.xml'
    _file = os.path.join(xml_dir, _file).replace(os.sep, '/')
    cmd = "aws s3 cp s3://dj.beatcloud.com/dj/xml/" \
          f"{config['XML_IMPORT_USER']}/rekordbox.xml {_file}"
    logger.info(cmd)
    os.system(cmd)
    rewrite_xml(config)

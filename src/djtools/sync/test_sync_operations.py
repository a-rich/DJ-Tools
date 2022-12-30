import os
import pytest
import shutil
from unittest import mock

from djtools.sync.sync_operations import (
    download_music, download_xml, upload_music, upload_xml
)
from djtools.utils.helpers import make_dirs
from test_data import MockOpen

pytest_plugins = [
    "test_data",
]


def test_download_music_no_usb(test_config):
    del test_config["USB_PATH"]
    with pytest.raises(KeyError):
        download_music(test_config)


def test_download_music_no_usb_path(test_config):
    test_config["USB_PATH"] = "/noexistent/path/to/USB/"
    with pytest.raises(FileNotFoundError):
        download_music(test_config)


def test_download_music(test_config, tmpdir, caplog):
    caplog.set_level("INFO")
    test_config["USB_PATH"] = tmpdir
    write_path = os.path.join(
        tmpdir, "DJ Music", "file.mp3"
    ).replace(os.sep, "/")
    cmd = [
        "aws",
        "s3",
        "sync",
        "s3://dj.beatcloud.com/dj/music/",
        os.path.dirname(write_path),
        "--size-only",
    ]
    with mock.patch(
        "djtools.sync.sync_operations.run_sync",
        side_effect=lambda *args, **kwargs: open(
            write_path, mode="w", encoding="utf-8",
        ).write("") 
    ) as mock_run_sync:
        download_music(test_config)
        mock_run_sync.assert_called_with(cmd)
    assert caplog.records[0].message == "Found 0 files"
    assert caplog.records[1].message == "Syncing remote track collection..."
    assert caplog.records[2].message == " ".join(cmd)
    assert caplog.records[3].message == "Found 1 new files"
    assert os.path.basename(caplog.records[4].message) == "file.mp3"


def test_download_xml_no_xml_path(test_config):
    del test_config["XML_PATH"]
    with pytest.raises(
        KeyError,
        match="Using the download_xml function of the sync_operations module "
            "requires the config option XML_PATH",
    ):
        download_xml(test_config)


def test_download_xml_no_xml(test_config):
    test_config["XML_PATH"] = ""
    with pytest.raises(
        FileNotFoundError,
        match="Using the download_xml function of the sync_operations module "
            "requires the config option XML_PATH to be valid",
    ):
        download_xml(test_config)


@mock.patch(
    "builtins.open", 
    MockOpen(
        files=["registered_users.json"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("test_user", "/test/USB/"),
    ).open,
)
def test_download_xml(test_config, test_xml, caplog):
    caplog.set_level("INFO")
    test_user = "test_user"
    other_user = "aweeeezy"
    new_xml = os.path.join(
        os.path.dirname(test_xml), f"{other_user}_rekordbox.xml"
    ).replace(os.sep, "/")
    shutil.copyfile(test_xml, new_xml)
    test_config["USER"] = test_user
    test_config["XML_IMPORT_USER"] = other_user
    test_config["XML_PATH"] = test_xml
    download_xml(test_config)
    cmd = [
        "aws",
        "s3",
        "cp",
        f's3://dj.beatcloud.com/dj/xml/{other_user}/rekordbox.xml',
        new_xml,
    ] 
    assert caplog.records[0].message == "Syncing remote rekordbox.xml..."
    assert caplog.records[1].message == " ".join(cmd)
    assert os.path.exists(new_xml)


def test_upload_music_no_usb(test_config):
    del test_config["USB_PATH"]
    with pytest.raises(
        KeyError,
        match="Using the upload_music function of the sync_operations module "
            "requires the config option USB_PATH",
    ):
        upload_music(test_config)


def test_upload_music_no_usb_path(test_config):
    test_config["USB_PATH"] = "/nonexistent/USB"
    with pytest.raises(
        FileNotFoundError,
        match=f'USB_PATH "{test_config["USB_PATH"]}" does not exist!'
    ):
        upload_music(test_config)


@pytest.mark.parametrize(
    "discord_url", ["", "https://discord.com/api/webhooks/some-id/"]
)
@mock.patch("djtools.sync.sync_operations.run_sync", return_value=None)
@mock.patch("djtools.sync.sync_operations.webhook", return_value=None)
def test_upload_music(
    mock_webhook, mock_run_sync, discord_url, tmpdir, test_config, caplog
):
    caplog.set_level("INFO")
    test_config["USB_PATH"] = tmpdir
    test_config["DISCORD_URL"] = discord_url
    test_dir = os.path.join(tmpdir, "DJ Music").replace(os.sep, "/") 
    make_dirs(test_dir)
    for file_name in [".test_file.mp3", "test_file.mp3"]:
        with open(
            os.path.join(test_dir, file_name).replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ) as file_:
            file_.write("")
    upload_music(test_config)
    cmd = [
        "aws",
        "s3",
        "sync",
        test_dir,
        "s3://dj.beatcloud.com/dj/music/",
        "--size-only",
    ]
    assert caplog.records[0].message == "Removed 1 files..."
    assert os.path.basename(caplog.records[1].message) == ".test_file.mp3"
    assert caplog.records[2].message == "Syncing track collection..."
    assert caplog.records[3].message == " ".join(cmd)
    assert len(os.listdir(test_dir)) == 1
    mock_run_sync.assert_called_with(cmd)
    if discord_url:
        mock_webhook.assert_called_with(
            "https://discord.com/api/webhooks/some-id/", content=None
        )


def test_upload_xml_no_xml_path(test_config):
    del test_config["XML_PATH"]
    with pytest.raises(
        KeyError,
        match="Using the upload_xml function of the sync_operations module "
            "requires the config option XML_PATH",
    ):
        upload_xml(test_config)


def test_upload_xml_no_xml(test_config):
    test_config["XML_PATH"] = "/nonexistent/USB"
    with pytest.raises(
        FileNotFoundError,
        match=f'XML_PATH "{test_config["XML_PATH"]}" does not exist!'
    ):
        upload_xml(test_config)


def test_upload_xml(test_config, test_xml, caplog):
    caplog.set_level("INFO")
    test_user = "test_user"
    test_config["USER"] = test_user
    test_config["XML_PATH"] = test_xml
    cmd = f"aws s3 cp {test_xml} s3://dj.beatcloud.com/dj/xml/{test_user}/"
    with mock.patch("os.system", return_value=None) as mock_os_system:
        upload_xml(test_config)
        mock_os_system.assert_called_with(cmd)
        assert caplog.records[0].message == (
            f"Uploading {test_user}'s rekordbox.xml..."
        )
        assert caplog.records[1].message == cmd

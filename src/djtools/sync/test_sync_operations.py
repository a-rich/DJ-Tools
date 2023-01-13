import os
import shutil
from unittest import mock

import pytest

from djtools.sync.sync_operations import (
    download_music, download_xml, upload_music, upload_xml
)
from djtools.utils.helpers import make_dirs
from test_data import MockOpen

pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize("playlist_name", ["", "playlist Uploads"])
@mock.patch(
    "djtools.sync.sync_operations.compare_tracks",
    return_value=(
        ["file.mp3"],
        ["playlist/file.mp3"],
    ),
)
def test_download_music(
    mock_compare_tracks, playlist_name, test_config, tmpdir, caplog
):
    caplog.set_level("INFO")
    test_config.USB_PATH = tmpdir
    test_config.DOWNLOAD_SPOTIFY = playlist_name
    write_path = os.path.join(
        tmpdir, "DJ Music", "file.mp3"
    ).replace(os.sep, "/")
    cmd = [
        "aws",
        "s3",
        "sync",
        "s3://dj.beatcloud.com/dj/music/",
        os.path.dirname(write_path),
    ]
    if playlist_name:
        cmd += ["--exclude", "*", "--include", "playlist/file.mp3"]
    cmd += ["--size-only"]
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


@mock.patch(
    "builtins.open", 
    MockOpen(
        files=["registered_users.yaml"],
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
    test_config.USER = test_user
    test_config.IMPORT_USER = other_user
    test_config.XML_PATH = test_xml
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


@pytest.mark.parametrize(
    "discord_url", ["", "https://discord.com/api/webhooks/some-id/"]
)
@mock.patch("djtools.sync.sync_operations.run_sync", return_value=None)
@mock.patch("djtools.sync.sync_operations.webhook", return_value=None)
def test_upload_music(
    mock_webhook, mock_run_sync, discord_url, tmpdir, test_config, caplog
):
    caplog.set_level("INFO")
    test_config.USB_PATH = tmpdir
    test_config.DISCORD_URL = discord_url
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


def test_upload_xml(test_config, test_xml, caplog):
    caplog.set_level("INFO")
    test_user = "test_user"
    test_config.USER = test_user
    test_config.XML_PATH = test_xml
    cmd = f"aws s3 cp {test_xml} s3://dj.beatcloud.com/dj/xml/{test_user}/"
    with mock.patch("os.system", return_value=None) as mock_os_system:
        upload_xml(test_config)
        mock_os_system.assert_called_with(cmd)
        assert caplog.records[0].message == (
            f"Uploading {test_user}'s rekordbox.xml..."
        )
        assert caplog.records[1].message == cmd

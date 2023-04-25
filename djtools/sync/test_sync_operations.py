from pathlib import Path
from unittest import mock

import pytest

from djtools.sync.sync_operations import (
    download_music, download_xml, upload_music, upload_xml
)
from djtools.utils.helpers import MockOpen


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
    write_path = Path(tmpdir) / "DJ Music" / "file.mp3"
    cmd = [
        "aws",
        "s3",
        "sync",
        "s3://dj.beatcloud.com/dj/music/",
        write_path.parent.as_posix(),
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
    assert Path(caplog.records[4].message).name == "file.mp3"


@mock.patch(
    "builtins.open", 
    MockOpen(
        files=["registered_users.yaml"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("test_user", "/test/USB/"),
    ).open,
)
@mock.patch("djtools.sync.sync_operations.rewrite_xml")
@mock.patch("subprocess.Popen.wait")
def test_download_xml(
    mock_subprocess, mock_rewrite_xml, test_config, test_xml, caplog
):
    caplog.set_level("INFO")
    test_user = "test_user"
    other_user = "aweeeezy"
    test_xml = Path(test_xml)
    new_xml = test_xml.parent / f"{other_user}_rekordbox.xml"
    new_xml.write_text(test_xml.read_text())
    test_config.USER = test_user
    test_config.IMPORT_USER = other_user
    test_config.XML_PATH = test_xml
    download_xml(test_config)
    cmd = [
        "aws",
        "s3",
        "cp",
        f's3://dj.beatcloud.com/dj/xml/{other_user}/rekordbox.xml',
        # NOTE(a-rich): since we could be passing a `test_xml` formatted as a
        # WindowsPath, the comparison needs to be made with `str(new_xml)`
        # (rather than `new_xml.as_posix()`).
        str(new_xml),
    ] 
    assert caplog.records[0].message == "Syncing remote rekordbox.xml..."
    assert caplog.records[1].message == " ".join(cmd)
    mock_rewrite_xml.assert_called_once()


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
    test_dir = Path(tmpdir) / "DJ Music"
    test_dir.mkdir(parents=True, exist_ok=True)
    for file_name in [".test_file.mp3", "test_file.mp3"]:
        with open(test_dir / file_name, mode="w", encoding="utf-8") as file_:
            file_.write("")
    upload_music(test_config)
    cmd = [
        "aws",
        "s3",
        "sync",
        test_dir.as_posix(),
        "s3://dj.beatcloud.com/dj/music/",
        "--size-only",
    ]
    assert caplog.records[0].message == "Removed 1 files..."
    assert Path(caplog.records[1].message).name == ".test_file.mp3"
    assert caplog.records[2].message == "Syncing track collection..."
    assert caplog.records[3].message == " ".join(cmd)
    assert len(list(test_dir.iterdir())) == 1
    mock_run_sync.assert_called_with(cmd)
    if discord_url:
        mock_webhook.assert_called_with(
            "https://discord.com/api/webhooks/some-id/", content=None
        )


@mock.patch("subprocess.Popen.wait")
def test_upload_xml(mock_subprocess, test_config, test_xml, caplog):
    caplog.set_level("INFO")
    test_user = "test_user"
    test_config.USER = test_user
    test_config.XML_PATH = test_xml
    cmd = f"aws s3 cp {test_xml} s3://dj.beatcloud.com/dj/xml/{test_user}/"
    upload_xml(test_config)
    assert caplog.records[0].message == (
        f"Uploading {test_user}'s rekordbox.xml..."
    )
    assert caplog.records[1].message == cmd

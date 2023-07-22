"""Testing for the sync_operations module."""
from pathlib import Path
from unittest import mock

import pytest

from djtools.sync.sync_operations import (
    download_collection, download_music, upload_collection, upload_music
)


@pytest.mark.parametrize("playlist_name", ["", "playlist Uploads"])
@mock.patch(
    "djtools.sync.sync_operations.compare_tracks",
    mock.Mock(
        return_value=(
            [Path("file.mp3")],
            [Path("playlist/file.mp3")],
        ),
    ),
)
def test_download_music(playlist_name, config, tmpdir, caplog):
    """Test for the download_music function."""
    caplog.set_level("INFO")
    config.USB_PATH = tmpdir
    config.DOWNLOAD_SPOTIFY_PLAYLIST = playlist_name
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

    def dummy_func():
        with open(write_path, mode="w", encoding="utf-8") as _file:
            _file.write("")

    with mock.patch(
        "djtools.sync.sync_operations.run_sync",
        side_effect=lambda *args, **kwargs: dummy_func()
    ) as mock_run_sync:
        download_music(config)
        mock_run_sync.assert_called_with(cmd)
    assert caplog.records[0].message == "Downloading track collection..."
    assert caplog.records[1].message == f"Found 0 files at {config.USB_PATH}"
    assert caplog.records[2].message == " ".join(cmd)
    assert caplog.records[3].message == "Found 1 new files"
    assert Path(caplog.records[4].message).name == "file.mp3"


@mock.patch("djtools.utils.helpers.get_spotify_client", mock.Mock())
def test_download_spotify_playlist_handles_no_matches(config, caplog):
    """Test for the download_music function."""
    caplog.set_level("WARNING")
    config.DOWNLOAD_SPOTIFY_PLAYLIST = "not-a-real-user Uploads"
    beatcloud_tracks = download_music(config)
    assert not beatcloud_tracks
    assert caplog.records[0].message == (
        "not-a-real-user Uploads not in spotify_playlists.yaml"
    )
    assert caplog.records[1].message == (
        "There are no Spotify tracks; make sure CHECK_TRACKS_SPOTIFY_PLAYLISTS"
        " has one or more keys from spotify_playlists.yaml"
    )
    assert caplog.records[2].message == (
        "No Beatcloud matches were found! Make sure you've supplied to correct"
        " playlist name."
    )


@pytest.mark.parametrize("collection_is_dir", [True, False])
@mock.patch("djtools.sync.sync_operations.rewrite_track_paths")
@mock.patch("djtools.sync.sync_operations.Popen")
def test_download_collection(
    mock_popen,
    mock_rewrite_track_paths,
    collection_is_dir,
    config,
    rekordbox_xml,
    caplog,
):
    """Test for the download_collection function."""
    caplog.set_level("INFO")
    test_user = "test_user"
    other_user = "aweeeezy"
    new_xml = rekordbox_xml.parent / f"{other_user}_rekordbox.xml"
    new_xml.write_text(rekordbox_xml.read_text(encoding="utf-8"), encoding="utf-8")
    config.USER = test_user
    config.IMPORT_USER = other_user
    config.COLLECTION_PATH = rekordbox_xml
    config.PLATFORM = "rekordbox"
    process = mock_popen.return_value.__enter__.return_value
    process.wait.return_value = 0
    with mock.patch(
        "djtools.sync.sync_operations.Path.is_dir",
        lambda path: collection_is_dir,
    ):
        download_collection(config)
    cmd = [
        "aws",
        "s3",
        "cp",
        f"s3://dj.beatcloud.com/dj/collections/{other_user}/"
        f"{config.PLATFORM}_collection",
        # NOTE(a-rich): since we could be passing a `rekordbox_xml` formatted
        # as a WindowsPath, the comparison needs to be made with `str(new_xml)`
        # (rather than `new_xml.as_posix()`).
        new_xml.as_posix(),
    ]
    if collection_is_dir:
        cmd.append("--recursive")
    assert caplog.records[0].message == (
        f"Downloading {config.IMPORT_USER}'s {config.PLATFORM} collection..."
    )
    assert caplog.records[1].message == " ".join(cmd)
    mock_rewrite_track_paths.assert_called_once()


@pytest.mark.parametrize(
    "discord_url", ["", "https://discord.com/api/webhooks/some-id/"]
)
@mock.patch("djtools.sync.sync_operations.run_sync", return_value=None)
@mock.patch("djtools.sync.sync_operations.webhook", return_value=None)
def test_upload_music(
    mock_webhook, mock_run_sync, discord_url, tmpdir, config, caplog
):
    """Test for the upload_music function."""
    caplog.set_level("INFO")
    config.USB_PATH = tmpdir
    config.DISCORD_URL = discord_url
    test_dir = Path(tmpdir) / "DJ Music"
    test_dir.mkdir(parents=True, exist_ok=True)
    for file_name in [".test_file.mp3", "test_file.mp3"]:
        with open(test_dir / file_name, mode="w", encoding="utf-8") as file_:
            file_.write("")
    upload_music(config)
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
    assert caplog.records[2].message == "Uploading track collection..."
    assert caplog.records[3].message == " ".join(cmd)
    assert len(list(test_dir.iterdir())) == 1
    mock_run_sync.assert_called_with(cmd)
    if discord_url:
        mock_webhook.assert_called_with(
            "https://discord.com/api/webhooks/some-id/", content=None
        )


@pytest.mark.parametrize("collection_is_dir", [True, False])
@mock.patch("djtools.sync.sync_operations.Popen")
def test_upload_collection(
    mock_popen, collection_is_dir, config, rekordbox_xml, caplog
):
    """Test for the upload_collection function."""
    caplog.set_level("INFO")
    user = "user"
    config.USER = user
    config.COLLECTION_PATH = rekordbox_xml
    config.PLATFORM = "rekordbox"
    cmd = (
        f"aws s3 cp {config.COLLECTION_PATH.as_posix()} "
        f"s3://dj.beatcloud.com/dj/collections/{user}/"
        f"{config.PLATFORM}_collection"
    )
    if collection_is_dir:
        cmd += " --recursive"
    process = mock_popen.return_value.__enter__.return_value
    process.wait.return_value = 0
    with mock.patch(
        "djtools.sync.sync_operations.Path.is_dir",
        lambda path: collection_is_dir,
    ):
        upload_collection(config)
    assert caplog.records[0].message == (
        f"Uploading {user}'s {config.PLATFORM} collection..."
    )
    assert caplog.records[1].message == cmd

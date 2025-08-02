"""Testing for the sync_operations module."""

from pathlib import Path
from unittest import mock

import pytest

from djtools.collection.config import RegisteredPlatforms
from djtools.sync.sync_operations import (
    download_collection,
    download_music,
    upload_collection,
    upload_music,
)


# pylint: disable=duplicate-code
TEST_BUCKET = "s3://some-bucket.com"


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
    config.sync.bucket_url = TEST_BUCKET
    config.sync.usb_path = tmpdir
    config.sync.download_spotify_playlist = playlist_name
    write_path = Path(tmpdir) / "DJ Music" / "file.mp3"
    cmd = [
        "aws",
        "s3",
        "sync",
        f"{TEST_BUCKET}/dj/music/",
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
        side_effect=lambda *args, **kwargs: dummy_func(),
    ) as mock_run_sync:
        download_music(config)
        mock_run_sync.assert_called_with(cmd, TEST_BUCKET)
    assert caplog.records[0].message == "Downloading track collection..."
    assert (
        caplog.records[1].message == f"Found 0 files at {config.sync.usb_path}"
    )
    assert caplog.records[2].message == " ".join(cmd)
    assert caplog.records[3].message == "Found 1 new files"
    assert Path(caplog.records[4].message).name == "file.mp3"


@mock.patch("djtools.utils.helpers.get_spotify_client", mock.Mock())
def test_download_spotify_playlist_handles_no_matches(config, caplog):
    """Test for the download_music function."""
    caplog.set_level("WARNING")
    config.sync.download_spotify_playlist = "not-a-real-user Uploads"
    beatcloud_tracks = download_music(config)
    assert not beatcloud_tracks
    assert caplog.records[0].message == (
        "not-a-real-user Uploads not in spotify_playlists.yaml"
    )
    assert caplog.records[1].message == (
        "There are no Spotify tracks; make sure download_spotify_playlist is "
        "a key in spotify_playlists.yaml"
    )
    assert caplog.records[2].message == (
        "No Beatcloud matches were found! Make sure you've supplied the "
        "correct playlist name."
    )


@pytest.mark.parametrize("collection_is_dir", [True, False])
@pytest.mark.parametrize("user_is_import_user", [True, False])
@mock.patch("djtools.sync.sync_operations.rewrite_track_paths")
@mock.patch("djtools.sync.sync_operations.Popen")
def test_download_collection(
    mock_popen,
    mock_rewrite_track_paths,
    collection_is_dir,
    user_is_import_user,
    config,
    rekordbox_xml,
    caplog,
):
    """Test for the download_collection function."""
    caplog.set_level("INFO")
    test_user = "test_user"
    other_user = "other_user"
    import_user = test_user if user_is_import_user else other_user
    config.sync.bucket_url = TEST_BUCKET
    config.sync.user = test_user
    config.sync.import_user = import_user
    config.collection.collection_path = rekordbox_xml
    config.collection.platform = RegisteredPlatforms.REKORDBOX
    new_xml = rekordbox_xml.parent / f"{import_user}_rekordbox.xml"
    new_xml.write_text(
        rekordbox_xml.read_text(encoding="utf-8"), encoding="utf-8"
    )
    process = mock_popen.return_value.__enter__.return_value
    process.wait.return_value = 0
    cmd = [
        "aws",
        "s3",
        "cp",
        f"{TEST_BUCKET}/dj/collections/{import_user}/"
        f"{config.collection.platform.value}_collection",
        # NOTE(a-rich): since we could be passing a `rekordbox_xml` formatted
        # as a WindowsPath, the comparison needs to be made with `str(new_xml)`
        # (rather than `new_xml.as_posix()`).
        new_xml.as_posix(),
    ]
    if collection_is_dir:
        cmd.append("--recursive")
    with mock.patch(
        "djtools.sync.sync_operations.Path.is_dir",
        lambda path: collection_is_dir,
    ):
        download_collection(config)
    mock_popen.assert_called_with(cmd)
    assert caplog.records[0].message == (
        f"Downloading {config.sync.import_user}'s {config.collection.platform.value} collection..."
    )
    assert caplog.records[1].message == " ".join(cmd)
    if not user_is_import_user:
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
    config.sync.bucket_url = TEST_BUCKET
    config.sync.usb_path = tmpdir
    config.sync.discord_url = discord_url
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
        f"{TEST_BUCKET}/dj/music/",
        "--size-only",
    ]
    assert caplog.records[0].message == "Removed 1 files..."
    assert Path(caplog.records[1].message).name == ".test_file.mp3"
    assert caplog.records[2].message == "Uploading track collection..."
    assert caplog.records[3].message == " ".join(cmd)
    assert len(list(test_dir.iterdir())) == 1
    mock_run_sync.assert_called_with(cmd, TEST_BUCKET)
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
    config.sync.bucket_url = TEST_BUCKET
    config.sync.user = user
    config.collection.collection_path = rekordbox_xml
    config.collection.platform = RegisteredPlatforms.REKORDBOX
    cmd = [
        "aws",
        "s3",
        "cp",
        config.collection.collection_path.as_posix(),
        f"{TEST_BUCKET}/dj/collections/{user}/{config.collection.platform.value}_collection",
    ]
    if collection_is_dir:
        cmd.append("--recursive")
    process = mock_popen.return_value.__enter__.return_value
    process.wait.return_value = 0
    with mock.patch(
        "djtools.sync.sync_operations.Path.is_dir",
        lambda path: collection_is_dir,
    ):
        upload_collection(config)
    assert caplog.records[0].message == (
        f"Uploading {user}'s {config.collection.platform.value} collection..."
    )
    assert caplog.records[1].message == " ".join(cmd)
    mock_popen.assert_called_with(cmd)

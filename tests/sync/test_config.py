"""Testing for the config module."""

import os
from pathlib import Path
import re
from unittest import mock

import getpass
import pytest


from djtools.sync.config import SyncConfig


@pytest.mark.parametrize("download,upload", [(True, False), (False, True)])
def test_syncconfig_download_or_upload_without_usb_path(download, upload):
    """Test for the SyncConfig class."""
    cfg = {
        "AWS_PROFILE": "myprofile",
        "BUCKET_URL": "s3://some-bucket.com",
        "DOWNLOAD_MUSIC": download,
        "UPLOAD_MUSIC": upload,
        "USB_PATH": None,
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Config must include USB_PATH for both DOWNLOAD_MUSIC and "
            "UPLOAD_MUSIC sync operations"
        ),
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize("download,upload", [(True, False), (False, True)])
def test_syncconfig_download_or_upload_with_missing_usb_path(download, upload):
    """Test for the SyncConfig class."""
    usb_path = Path("not/real/usb/path")
    cfg = {
        "AWS_PROFILE": "myprofile",
        "BUCKET_URL": "s3://some-bucket.com",
        "DOWNLOAD_MUSIC": download,
        "UPLOAD_MUSIC": upload,
        "USB_PATH": usb_path,
    }
    with pytest.raises(
        RuntimeError,
        match=re.escape(f'Configured USB_PATH "{usb_path}" was not found!'),
    ):
        SyncConfig(**cfg)


def test_syncconfig_download_without_import_user():
    """Test for the SyncConfig class."""
    cfg = {
        "DOWNLOAD_COLLECTION": True,
        "AWS_PROFILE": "myprofile",
        "BUCKET_URL": "s3://some-bucket.com",
        "IMPORT_USER": "",
    }
    with pytest.raises(
        RuntimeError,
        match="IMPORT_USER must be set to download a collection",
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize("sync_direction", ["DOWN", "UP"])
def test_syncconfig_mutually_exclusive_dirs(sync_direction):
    """Test for the SyncConfig class."""
    cfg = {
        f"{sync_direction}LOAD_INCLUDE_DIRS": ["test"],
        f"{sync_direction}LOAD_EXCLUDE_DIRS": ["test"],
    }
    with pytest.raises(
        ValueError,
        match=(
            "Config must neither contain both UPLOAD_INCLUDE_DIRS and "
            "UPLOAD_EXCLUDE_DIRS or both DOWNLOAD_INCLUDE_DIRS and "
            "DOWNLOAD_EXCLUDE_DIRS"
        ),
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize(
    "aws_operation",
    [
        "DOWNLOAD_COLLECTION",
        "DOWNLOAD_MUSIC",
        "UPLOAD_COLLECTION",
        "UPLOAD_MUSIC",
    ],
)
def test_syncconfig_no_aws_profile(aws_operation):
    """Test for the SyncConfig class."""
    cfg = {"AWS_PROFILE": "", aws_operation: True}
    with pytest.raises(
        RuntimeError,
        match="Config must include AWS_PROFILE for sync operations",
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize(
    "aws_operation",
    [
        "DOWNLOAD_COLLECTION",
        "DOWNLOAD_MUSIC",
        "UPLOAD_COLLECTION",
        "UPLOAD_MUSIC",
    ],
)
def test_syncconfig_no_bucket(aws_operation):
    """Test for the SyncConfig class."""
    cfg = {"AWS_PROFILE": "default", aws_operation: True}
    with pytest.raises(
        RuntimeError,
        match="Config must include BUCKET_URL for sync operations",
    ):
        SyncConfig(**cfg)


def test_syncconfig_sets_aws_profile_env_var():
    """Test for the SyncConfig class."""
    cfg = {"AWS_PROFILE": "test-profile"}
    assert (
        os.environ.get("AWS_PROFILE")  # pylint: disable=no-member
        != cfg["AWS_PROFILE"]
    )
    SyncConfig(**cfg)
    assert (
        os.environ.get("AWS_PROFILE")  # pylint: disable=no-member
        == cfg["AWS_PROFILE"]
    )


@pytest.mark.parametrize(
    "input_user,output_user",
    [("", getpass.getuser()), ("test-user", "test-user")],
)
def test_syncconfig_set_user(input_user, output_user):
    """Test for the SyncConfig class."""
    cfg = {"USER": input_user}
    assert not SyncConfig.model_fields["USER"].default
    sync_config = SyncConfig(**cfg)
    assert sync_config.USER == output_user


@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def test_syncconfig_upload_without_discord_url(rekordbox_xml, caplog):
    """Test for the SyncConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "USB_PATH": ".",
        "UPLOAD_MUSIC": True,
        "BUCKET_URL": "s3://some-bucket.com",
        "DISCORD_URL": "",
        "COLLECTION_PATH": rekordbox_xml,
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
    }
    SyncConfig(**cfg)
    assert caplog.records[0].message == (
        'DISCORD_URL is not configured...set this for "New Music" '
        "discord messages!"
    )


@pytest.mark.parametrize(
    "path", ["some/path/string", Path("some/path/object")]
)
def test_syncconfig_usb_path_is_path(path):
    """Test for the SyncConfig class."""
    cfg = {"USB_PATH": path}
    sync_config = SyncConfig(**cfg)
    assert isinstance(sync_config.USB_PATH, Path)

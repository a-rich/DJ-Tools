"""Testing for the config module."""

import os
import re
from pathlib import Path
from unittest import mock

import getpass
import pytest


from djtools.sync.config import SyncConfig


@pytest.mark.parametrize("download,upload", [(True, False), (False, True)])
def test_syncconfig_download_or_upload_without_usb_path(download, upload):
    """Test for the SyncConfig class."""
    cfg = {
        "aws_profile": "myprofile",
        "bucket_url": "s3://some-bucket.com",
        "download_music": download,
        "upload_music": upload,
        "usb_path": None,
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Config must include usb_path for both download_music and "
            "upload_music sync operations"
        ),
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize("download,upload", [(True, False), (False, True)])
def test_syncconfig_download_or_upload_with_missing_usb_path(download, upload):
    """Test for the SyncConfig class."""
    usb_path = Path("not/real/usb/path")
    cfg = {
        "aws_profile": "myprofile",
        "bucket_url": "s3://some-bucket.com",
        "download_music": download,
        "upload_music": upload,
        "usb_path": usb_path,
    }
    with pytest.raises(
        RuntimeError,
        match=re.escape(f'Configured usb_path "{usb_path}" was not found!'),
    ):
        SyncConfig(**cfg)


def test_syncconfig_download_without_import_user():
    """Test for the SyncConfig class."""
    cfg = {
        "download_collection": True,
        "aws_profile": "myprofile",
        "bucket_url": "s3://some-bucket.com",
        "import_user": "",
    }
    with pytest.raises(
        RuntimeError,
        match="import_user must be set to download a collection",
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize("sync_direction", ["down", "up"])
def test_syncconfig_mutually_exclusive_dirs(sync_direction):
    """Test for the SyncConfig class."""
    cfg = {
        f"{sync_direction}load_include_dirs": ["test"],
        f"{sync_direction}load_exclude_dirs": ["test"],
    }
    with pytest.raises(
        ValueError,
        match=(
            "Config must neither contain both upload_include_dirs and "
            "upload_exclude_dirs or both download_include_dirs and "
            "download_exclude_dirs"
        ),
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize(
    "aws_operation",
    [
        "download_collection",
        "download_music",
        "upload_collection",
        "upload_music",
    ],
)
def test_syncconfig_no_aws_profile(aws_operation):
    """Test for the SyncConfig class."""
    cfg = {"aws_profile": "", aws_operation: True}
    with pytest.raises(
        RuntimeError,
        match="Config must include aws_profile for sync operations",
    ):
        SyncConfig(**cfg)


@pytest.mark.parametrize(
    "aws_operation",
    [
        "download_collection",
        "download_music",
        "upload_collection",
        "upload_music",
    ],
)
def test_syncconfig_no_bucket(aws_operation):
    """Test for the SyncConfig class."""
    cfg = {"aws_profile": "default", aws_operation: True}
    with pytest.raises(
        RuntimeError,
        match="Config must include bucket_url for sync operations",
    ):
        SyncConfig(**cfg)


def test_syncconfig_sets_aws_profile_env_var():
    """Test for the SyncConfig class."""
    cfg = {"aws_profile": "test-profile"}
    assert (
        os.environ.get("AWS_PROFILE")  # pylint: disable=no-member
        != cfg["aws_profile"]
    )
    SyncConfig(**cfg)
    assert (
        os.environ.get("AWS_PROFILE")  # pylint: disable=no-member
        == cfg["aws_profile"]
    )


@pytest.mark.parametrize(
    "input_user,output_user",
    [("", getpass.getuser()), ("test-user", "test-user")],
)
def test_syncconfig_set_user(input_user, output_user):
    """Test for the SyncConfig class."""
    cfg = {"user": input_user}
    assert not SyncConfig.model_fields.get("user").default
    sync_config = SyncConfig(**cfg)
    assert sync_config.user == output_user


@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def test_syncconfig_upload_without_discord_url(caplog):
    """Test for the SyncConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "bucket_url": "s3://some-bucket.com",
        "discord_url": "",
        "upload_music": True,
        "usb_path": ".",
    }
    SyncConfig(**cfg)
    assert caplog.records[0].message == (
        'discord_url is not configured...set this for "New Music" '
        "discord messages!"
    )


@pytest.mark.parametrize(
    "path", ["some/path/string", Path("some/path/object")]
)
def test_syncconfig_usb_path_is_path(path):
    """Test for the SyncConfig class."""
    cfg = {"usb_path": path}
    sync_config = SyncConfig(**cfg)
    assert isinstance(sync_config.usb_path, Path)

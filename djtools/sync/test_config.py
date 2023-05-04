"""Testing for the config module."""
from unittest import mock

import getpass
import pytest


from djtools.sync.config import SyncConfig
from djtools.utils.helpers import mock_exists, MockOpen


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.yaml"],
        content="bad:\tfile",
    ).open,
)
def test_syncconfig_bad_registered_users():
    """Test for the SyncConfig class."""
    with pytest.raises(
        RuntimeError,
        match="Error reading registered_users.yaml",
    ):
        SyncConfig()


@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"],
    write_only=True).open,
)
@pytest.mark.parametrize("operations", [(True, False), (False, True)])
@pytest.mark.parametrize("usb_path", ["", "nonexistent/path"])
def test_syncconfig_download_or_upload_without_usb_path(operations, usb_path):
    """Test for the SyncConfig class."""
    download, upload = operations
    cfg = {
        "AWS_PROFILE": "myprofile",
        "DOWNLOAD_MUSIC": download,
        "UPLOAD_MUSIC": upload,
        "USB_PATH": usb_path,
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Config must include USB_PATH for both DOWNLOAD_MUSIC and "
            "UPLOAD_MUSIC sync operations"
        ),
    ):
        SyncConfig(**cfg)


def test_syncconfig_download_without_import_user():
    """Test for the SyncConfig class."""
    cfg = {
        "DOWNLOAD_XML": True,
        "AWS_PROFILE": "myprofile",
        "IMPORT_USER": "not a valid user",
    }
    with pytest.raises(
        RuntimeError,
        match=(
            "Unable to import from XML of unregistered IMPORT_USER "
            f'"{cfg["IMPORT_USER"]}"'
        ),
    ):
        SyncConfig(**cfg)


def test_syncconfig_mutually_exclusive_dirs():
    """Test for the SyncConfig class."""
    cfg = {"UPLOAD_INCLUDE_DIRS": ["test"], "UPLOAD_EXCLUDE_DIRS": ["test"]}
    with pytest.raises(
        ValueError,
        match=(
            "Config must neither contain both UPLOAD_INCLUDE_DIRS and "
            "UPLOAD_EXCLUDE_DIRS or both DOWNLOAD_INCLUDE_DIRS and "
            "DOWNLOAD_EXCLUDE_DIRS"
        ),
    ):
        SyncConfig(**cfg)


def test_syncconfig_no_aws_profile():
    """Test for the SyncConfig class."""
    cfg = {"AWS_PROFILE": "", "UPLOAD_XML": True}
    with pytest.raises(
        RuntimeError,
        match="Config must include AWS_PROFILE for sync operations"
    ):
        SyncConfig(**cfg)


@mock.patch(
    "djtools.sync.config.Path.exists",
    lambda path: mock_exists([("registered_users.yaml", False)], path)
)
@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"],
    write_only=True).open,
)
@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def test_syncconfig_no_registered_users(test_xml, caplog):
    """Test for the SyncConfig class."""
    cfg = {
        "XML_PATH": test_xml,
        "SPOTIFY_CLIENT_ID": "id",
        "SPOTIFY_CLIENT_SECRET": "secret",
        "SPOTIFY_REDIRECT_URI": "uri",
        "SPOTIFY_USERNAME": "name",
    }
    caplog.set_level("WARNING")
    SyncConfig(**cfg)
    assert caplog.records[0].message == "No registered users!"


@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"],
    write_only=True).open,
)
def test_syncconfig_set_user():
    """Test for the SyncConfig class."""
    cfg = {"USER": ""}
    assert not SyncConfig.__fields__["USER"].default
    sync_config = SyncConfig(**cfg)
    assert sync_config.USER == getpass.getuser()


@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"],
    write_only=True).open,
)
@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def test_syncconfig_upload_without_discord_url(test_xml, caplog):
    """Test for the SyncConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "USB_PATH": ".",
        "UPLOAD_MUSIC": True,
        "DISCORD_URL": "",
        "XML_PATH": test_xml,
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

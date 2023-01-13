from unittest import mock

import getpass
import pytest


from djtools.sync.config import SyncConfig
from test_data import MockExists, MockOpen


pytest_plugins = [
    "test_data",
]


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.yaml"],
        content="bad:\tfile",
    ).open,
)
def test_syncconfig_bad_registered_users():
    with pytest.raises(
        RuntimeError,
        match="Error reading registered_users.yaml",
    ):
        SyncConfig()


def test_syncconfig_download_without_import_user():
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
    cfg = {"AWS_PROFILE": "", "UPLOAD_XML": True}
    with pytest.raises(
        RuntimeError,
        match="Config must include AWS_PROFILE for sync operations"
    ):
        SyncConfig(**cfg)


@mock.patch("builtins.open", MockOpen(files=["registered_users.yaml"], write_only=True).open)
@mock.patch(
    "djtools.sync.config.os.path.exists",
    MockExists(
        files=[
            ("registered_users.yaml", False),
        ]
    ).exists,
)
@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_syncconfig_no_registered_users(mock_get_spotify_client, test_xml, caplog):
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


@mock.patch("builtins.open", MockOpen(files=["registered_users.yaml"], write_only=True).open)
def test_syncconfig_set_user():
    cfg = {"USER": ""}
    assert not SyncConfig.__fields__["USER"].default
    sync_config = SyncConfig(**cfg)
    assert sync_config.USER == getpass.getuser()


@mock.patch("builtins.open", MockOpen(files=["registered_users.yaml"], write_only=True).open)
@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_syncconfig_upload_without_discord_url(
    mock_get_spotify_client, test_xml, caplog
):
    caplog.set_level("WARNING")
    cfg = {
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

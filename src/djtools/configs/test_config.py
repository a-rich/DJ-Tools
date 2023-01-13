from subprocess import PIPE
from unittest import mock

import pytest

from djtools.configs.config import BaseConfig


def test_baseconfig_aws_profile():
    BaseConfig()


def test_baseconfig_aws_profile_not_set(caplog):
    caplog.set_level("WARNING")
    cfg = {"AWS_PROFILE": ""}
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "Without AWS_PROFILE set to a valid profile ('default' or otherwise) "
        "you cannot use any of the following features: CHECK_TRACKS, "
        "DOWNLOAD_MUSIC, DOWNLOAD_XML, UPLOAD_MUSIC, UPLOAD_XML"
    )


# TODO(a-rich): Figure out why awscli fails in the test runner.
# def test_baseconfig_aws_profile_invalid():
#     cfg = {"AWS_PROFILE": "definitely not a real AWS profile"}
#     with pytest.raises(
#         RuntimeError, match="AWS_PROFILE is not a valid profile!"
#     ):
#         BaseConfig(**cfg)

 
# @mock.patch("djtools.configs.config.Popen", side_effect=Exception())
# def test_baseconfig_awscli_not_installed(mock_popen):
#     cfg = {"AWS_PROFILE": "definitely not a real AWS profile"}
#     with pytest.raises(
#         RuntimeError,
#         match=(
#             "Failed to run AWS command; make sure you've installed awscli "
#             "correctly."
#         )
#     ):
#         BaseConfig(**cfg)


def test_baseconfig_no_xml_path(caplog):
    caplog.set_level("WARNING")
    cfg = {
        "AWS_PROFILE": "default",
        "SPOTIFY_CLIENT_ID": "",
        "XML_PATH": "",
    }
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "XML_PATH is not set. Without this set to a valid Rekordbox XML "
        "export, you cannot use the following features: "
        "COPY_PLAYLISTS, DOWNLOAD_XML, RANDOMIZE_PLAYLISTS, "
        "REKORDBOX_PLAYLISTS, UPLOAD_XML"
    )


def test_baseconfig_xml_path_does_not_exist(caplog):
    caplog.set_level("WARNING")
    cfg = {
        "AWS_PROFILE": "default",
        "SPOTIFY_CLIENT_ID": "",
        "XML_PATH": "nonexistent XML",
    }
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "XML_PATH does not exist. Without this set to a valid "
        "Rekordbox XML export, you cannot use the following features: "
        "COPY_PLAYLISTS, DOWNLOAD_XML, RANDOMIZE_PLAYLISTS, "
        "REKORDBOX_PLAYLISTS, UPLOAD_XML"
    )

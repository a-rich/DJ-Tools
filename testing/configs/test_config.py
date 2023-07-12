"""Testing for the config module."""
from djtools.configs.config import BaseConfig


def test_baseconfig_aws_profile():
    """Test for the BaseConfig class."""
    BaseConfig()


def test_baseconfig_aws_profile_not_set(caplog):
    """Test for the BaseConfig class."""
    caplog.set_level("WARNING")
    cfg = {"AWS_PROFILE": ""}
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "Without AWS_PROFILE set to a valid profile ('default' or otherwise) "
        "you cannot use any of the following features: CHECK_TRACKS, "
        "DOWNLOAD_MUSIC, DOWNLOAD_COLLECTION, UPLOAD_MUSIC, UPLOAD_COLLECTION"
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


def test_baseconfig_no_collection_path(caplog):
    """Test for the BaseConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "AWS_PROFILE": "default",
        "SPOTIFY_CLIENT_ID": "",
        "COLLECTION_PATH": None,
    }
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "COLLECTION_PATH is not set. Without this set to a valid collection, "
        "you cannot use the following features: COLLECTION_PLAYLISTS, "
        "COPY_PLAYLISTS, DOWNLOAD_COLLECTION, SHUFFLE_PLAYLISTS, "
        "UPLOAD_COLLECTION"
    )


def test_baseconfig_collection_path_does_not_exist(caplog):
    """Test for the BaseConfig class."""
    caplog.set_level("WARNING")
    cfg = {
        "AWS_PROFILE": "default",
        "SPOTIFY_CLIENT_ID": "",
        "COLLECTION_PATH": "nonexistent collection",
    }
    BaseConfig(**cfg)
    assert caplog.records[0].message == (
        "COLLECTION_PATH does not exist. Without this set to a valid "
        "collection, you cannot use the following features: "
        "COLLECTION_PLAYLISTS, COPY_PLAYLISTS, DOWNLOAD_COLLECTION, "
        "SHUFFLE_PLAYLISTS, UPLOAD_COLLECTION"
    )

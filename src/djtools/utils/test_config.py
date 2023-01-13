import pytest

from djtools.utils.config import UtilsConfig


def test_utilsconfig():
    cfg = {"CHECK_TRACKS": True, "AWS_PROFILE": "default"}
    UtilsConfig(**cfg)


def test_utilsconfig_no_aws_profile():
    cfg = {"CHECK_TRACKS": True, "AWS_PROFILE": ""}
    with pytest.raises(
        ValueError, match="Config must include AWS_PROFILE for CHECK_TRACKS",
    ):
        UtilsConfig(**cfg)

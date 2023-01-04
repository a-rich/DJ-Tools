import os
from unittest import mock

import pytest
from youtube_dl.utils import DownloadError

from djtools.utils.youtube_dl import fix_up, youtube_dl


pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize(
    "test_assets",
    [
        (
            "Some Artist - Some Track-1224569284.mp3",
            "Some Track - Some Artist.mp3",
        ),
        (
            "Some Artist-891238 - Some Track-1224569284.wav",
            "Some Track - Some Artist-891238.wav",
        ),
        (
            "Some Artist - Some Track.mp3",
            "Some Track - Some Artist.mp3",
        ),
    ],
)
def test_fix_up(test_assets):
    test_file, expected_clean_file = test_assets
    clean_file = fix_up(test_file)
    assert clean_file == expected_clean_file


def test_youtube_dl(tmpdir, test_config):
    test_config.YOUTUBE_DL_URL = (
        "https://soundcloud.com/aweeeezy_music/sets/test-download"
    )
    test_config.YOUTUBE_DL_LOCATION = tmpdir
    with mock.patch(
        "youtube_dl.YoutubeDL",
    ) as mock_ytdl:
        context = mock_ytdl.return_value.__enter__.return_value 
        context.download.side_effect = lambda *args, **kwargs: open(
            os.path.join(tmpdir, "file.mp3").replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ).write("")
        youtube_dl(test_config)
    assert len(os.listdir(tmpdir)) == 1


def test_youtube_dl_invalid_url(test_config):
    test_config.YOUTUBE_DL_URL = ""
    with pytest.raises(DownloadError):
        youtube_dl(test_config)

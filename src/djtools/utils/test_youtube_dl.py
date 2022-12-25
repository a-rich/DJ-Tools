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
    test_config["YOUTUBE_DL_URL"] = (
        "https://soundcloud.com/aweeeezy_music/sets/test-download"
    )
    new_dir = os.path.join(tmpdir, "new_dir")
    test_config["YOUTUBE_DL_LOCATION"] = new_dir
    with mock.patch(
        "youtube_dl.YoutubeDL.download",
        side_effect=lambda *args, **kwargs: open(
            os.path.join(new_dir, "file.mp3"), mode="w", encoding="utf-8"
        ).write("")
    ) as mock_ytdl:
        youtube_dl(test_config)
    assert len(os.listdir(new_dir)) == 1


def test_youtube_dl_no_url(test_config):
    del test_config["YOUTUBE_DL_URL"]
    with pytest.raises(KeyError):
        youtube_dl(test_config)
    

def test_youtube_dl_invalid_url(test_config):
    test_config["YOUTUBE_DL_URL"] = ""
    with pytest.raises(DownloadError):
        youtube_dl(test_config)
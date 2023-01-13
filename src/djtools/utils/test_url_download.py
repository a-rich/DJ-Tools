import os
from unittest import mock

import pytest
from youtube_dl.utils import DownloadError

from djtools.utils.url_download import fix_up, url_download


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


def test_url_download(tmpdir, test_config):
    test_config.URL_DOWNLOAD = (
        "https://soundcloud.com/aweeeezy_music/sets/test-download"
    )
    test_config.URL_DOWNLOAD_DESTINATION = tmpdir
    with mock.patch(
        "youtube_dl.YoutubeDL",
    ) as mock_ytdl:
        context = mock_ytdl.return_value.__enter__.return_value 
        context.download.side_effect = lambda *args, **kwargs: open(
            os.path.join(tmpdir, "file.mp3").replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ).write("")
        url_download(test_config)
    assert len(os.listdir(tmpdir)) == 1


def test_url_download_invalid_url(test_config):
    test_config.URL_DOWNLOAD = ""
    with pytest.raises(DownloadError):
        url_download(test_config)

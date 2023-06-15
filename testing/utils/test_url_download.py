"""Testing for the url_download module."""
from pathlib import Path
from unittest import mock

import pytest
from youtube_dl.utils import DownloadError

from djtools.utils.url_download import fix_up, url_download


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
    """Test for the fix_up function."""
    test_file, expected_clean_file = map(Path, test_assets)
    clean_file = fix_up(test_file)
    assert clean_file == expected_clean_file


def test_url_download(tmpdir, test_config):
    """Test for the url_download function."""
    tmpdir = Path(tmpdir)
    test_config.URL_DOWNLOAD = (
        "https://soundcloud.com/aweeeezy_music/sets/test-download"
    )
    test_config.URL_DOWNLOAD_DESTINATION = tmpdir

    def dummy_func():
        with open(tmpdir / "file.mp3", mode="w", encoding="utf-8") as _file:
            _file.write("")

    with mock.patch(
        "youtube_dl.YoutubeDL",
    ) as mock_ytdl:
        context = mock_ytdl.return_value.__enter__.return_value
        context.download.side_effect = lambda *args, **kwargs: dummy_func()
        url_download(test_config)
    assert len(list(tmpdir.iterdir())) == 1


def test_url_download_invalid_url(test_config):
    """Test for the url_download function."""
    test_config.URL_DOWNLOAD = ""
    with pytest.raises(DownloadError):
        url_download(test_config)

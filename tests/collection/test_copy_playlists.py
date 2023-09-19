"""Testing for the copy_playlists module."""
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.collection.copy_playlists import copy_playlists


def test_copy_playlists(tmpdir, config, rekordbox_xml):
    """Test for the copy_playlists function."""
    target_playlists = ["Hip Hop", "Dark"]
    test_output_dir = Path(tmpdir) / "output"
    config.COLLECTION_PATH = rekordbox_xml
    config.COPY_PLAYLISTS = target_playlists
    config.COPY_PLAYLISTS_DESTINATION = Path(test_output_dir)
    new_collection = (
        config.COPY_PLAYLISTS_DESTINATION
        / f"copied_playlists_collection{config.COLLECTION_PATH.suffix}"
    )
    copy_playlists(config)
    assert list(test_output_dir.iterdir())
    assert new_collection.exists()
    with open(new_collection, mode="r", encoding="utf-8") as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        assert any(x in track["Genre"] for x in target_playlists)
        assert test_output_dir.as_posix() in unquote(track["Location"])


def test_copy_playlists_invalid_playlist(tmpdir, config, rekordbox_xml):
    """Test for the copy_playlists function."""
    playlist = "invalid_playlist"
    config.COLLECTION_PATH = rekordbox_xml
    config.COPY_PLAYLISTS = [playlist]
    config.COPY_PLAYLISTS_DESTINATION = Path(tmpdir)
    with pytest.raises(LookupError, match=f"{playlist} not found"):
        copy_playlists(config)

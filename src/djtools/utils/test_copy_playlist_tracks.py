import inspect
import os
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.utils.copy_playlists_tracks import copy_file, copy_playlists_tracks


pytest_plugins = [
 "test_data",
]


def test_copy_file(tmpdir, test_track):
    dest_dir = os.path.join(tmpdir, "output").replace(os.sep, "/")
    os.makedirs(dest_dir)
    old_track_loc = test_track["Location"]
    copy_file(track=test_track, destination=dest_dir)
    new_track_loc = test_track["Location"]
    loc_prefix = inspect.signature(
        copy_file
    ).parameters.get("loc_prefix").default
    new_file_path = os.path.join(
        dest_dir, os.path.basename(old_track_loc)
    ).replace(os.sep, "/")
    # New track location must have "file://localhost" prefix and the same
    # basename with the destination directory in between.
    assert new_track_loc == f"{loc_prefix}{new_file_path}"
    # New track file must exist at the new location.
    assert os.path.exists(unquote(new_file_path))


def test_copy_playlists_tracks(tmpdir, test_config, test_xml):
    target_playlists = ["Rock", "Pop"]
    new_xml = os.path.join(
        os.path.dirname(test_xml), "relocated_rekordbox.xml"
    ).replace(os.sep, "/")
    test_output_dir = os.path.join(tmpdir, "output").replace(os.sep, "/")
    test_config["XML_PATH"] = test_xml
    test_config["COPY_PLAYLISTS_TRACKS"] = target_playlists
    test_config["COPY_PLAYLISTS_TRACKS_DESTINATION"] = test_output_dir
    copy_playlists_tracks(test_config)
    # Output directory must contain copied files.
    assert os.listdir(test_output_dir)
    # New XML must be saved to file.
    assert os.path.exists(new_xml)
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        # Only tracks in the target playlist exist in the new XML.
        assert any(x in track["Genre"] for x in target_playlists)
        # All tracks in the new XML must have their "Location" updated.
        assert test_output_dir in unquote(track["Location"])
        

def test_copy_playlist_tracks_no_xml_path(test_config):
    test_config["XML_PATH"] = ""
    with pytest.raises(KeyError):
        copy_playlists_tracks(test_config)


def test_copy_playlist_tracks_no_xml_file(test_config):
    test_config["XML_PATH"] = "/some/nonexistent/rekordbox.xml"
    with pytest.raises(FileNotFoundError):
        copy_playlists_tracks(test_config)


@pytest.mark.parametrize("playlists", [[], ["Rock"]])
@pytest.mark.parametrize("destination", ["", "dest"])
def test_copy_playlist_tracks_no_playlists_or_destination(
    test_config, test_xml, playlists, destination
):
    test_config["XML_PATH"] = test_xml
    test_config["COPY_PLAYLISTS_TRACKS"] = playlists
    test_config["COPY_PLAYLISTS_TRACKS_DESTINATION"] = destination
    if not playlists and destination:
        with pytest.raises(KeyError):
            copy_playlists_tracks(test_config)


def test_copy_playlist_tracks_invalid_playlist(tmpdir, test_config, test_xml):
    test_config["XML_PATH"] = test_xml
    test_config["COPY_PLAYLISTS_TRACKS"] = ["invalid_playlist"]
    test_config["COPY_PLAYLISTS_TRACKS_DESTINATION"] = tmpdir
    with pytest.raises(LookupError):
        copy_playlists_tracks(test_config)

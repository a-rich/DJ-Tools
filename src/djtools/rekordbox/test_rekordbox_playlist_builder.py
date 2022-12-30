import json
import os
import shutil

import pytest

from djtools.rekordbox.rekordbox_playlist_builder import (
    PlaylistBuilder, rekordbox_playlists    
)


pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize(
    "remainder_type", ["", "folder", "playlist", "invalid"]
)
def test_playlistbuilder(remainder_type, test_xml, test_playlist_config):
    playlist_builder = PlaylistBuilder(
        rekordbox_database=test_xml,
        playlist_config=test_playlist_config,
        pure_genre_playlists=["Techno"],
        playlist_remainder_type=remainder_type
    )()


def test_playlistbuilder_no_xml(test_playlist_config):
    xml_path = "nonexistent.xml"
    with pytest.raises(
        FileNotFoundError,
        match=f"Rekordbox database {xml_path} does not exist!",
    ):
        PlaylistBuilder(
            rekordbox_database=xml_path,
            playlist_config=test_playlist_config,
        )()


def test_playlistbuilder_invalid_parser(
    tmpdir, test_xml, test_playlist_config
):
    new_playlist_config = os.path.join(
        tmpdir, os.path.basename(test_playlist_config)
    ).replace(os.sep, "/")
    shutil.copyfile(test_playlist_config, new_playlist_config)
    with open(new_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = json.load(_file)
    parser_type = "nonexistent_parser"
    playlist_config[parser_type] = {}
    with open(new_playlist_config, mode="w", encoding="utf-8",) as _file:
        playlist_config = json.dump(playlist_config, _file)
    with pytest.raises(
        AttributeError,
        match=f"{parser_type} is not a valid TagParser!"
    ):
        PlaylistBuilder(
            rekordbox_database=test_xml,
            playlist_config=new_playlist_config,
        )()


def test_playlistbuilder_invalid_playlist(
    tmpdir, test_xml, test_playlist_config
):
    new_playlist_config = os.path.join(
        tmpdir, os.path.basename(test_playlist_config)
    ).replace(os.sep, "/")
    shutil.copyfile(test_playlist_config, new_playlist_config)
    with open(new_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = json.load(_file)
    content = [0]
    playlist_config = {
        "GenreTagParser": {"name": "invalid", "playlists": content}
    }
    with open(new_playlist_config, mode="w", encoding="utf-8",) as _file:
        playlist_config = json.dump(playlist_config, _file)
    with pytest.raises(
        ValueError,
        match=f"Encountered invalid input type {type(content[0])}: {content[0]}"
    ):
        PlaylistBuilder(
            rekordbox_database=test_xml,
            playlist_config=new_playlist_config,
        )()


def test_rekordbox_playlists(test_config, test_xml):
    test_config["XML_PATH"] = test_xml
    rekordbox_playlists(test_config)


def test_rekordbox_playlists_no_xml(test_config):
    test_config["XML_PATH"] = ""
    with pytest.raises(
        KeyError,
        match="Using the rekordbox_playlist_builder module requires the "
            "config option XML_PATH",
    ):
        rekordbox_playlists(test_config)
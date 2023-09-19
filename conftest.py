"""This module contains fixtures for DJ Tools."""
from argparse import Namespace
import os
from pathlib import Path

# import time
from unittest import mock

from bs4 import BeautifulSoup
from pydub import AudioSegment, generators
import pytest
import yaml

from djtools.configs.config import BaseConfig
from djtools.configs.helpers import filter_dict, PKG_CFG
from djtools.collection.collections import RekordboxCollection
from djtools.collection.playlists import RekordboxPlaylist
from djtools.collection.tracks import RekordboxTrack


@pytest.fixture
def namespace():
    """Test Namespace object fixture."""
    return Namespace(link_configs=False, log_level="INFO", version=False)


@pytest.fixture
@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def config():
    """Test config fixture."""
    configs = {pkg: cfg() for pkg, cfg in PKG_CFG.items() if pkg != "configs"}
    joined_config = BaseConfig(
        **{
            k: v
            for cfg in configs.values()
            for k, v in filter_dict(cfg).items()
        }
    )

    return joined_config


@pytest.fixture(scope="session")
def input_tmpdir(tmpdir_factory):
    """Test tmpdir fixture."""
    return tmpdir_factory.mktemp("input")


@pytest.fixture(scope="session")
def audio_file(input_tmpdir):  # pylint: disable=redefined-outer-name
    """Test audio file fixture."""
    headroom = -2
    audio = AudioSegment.silent(duration=1000).overlay(
        generators.WhiteNoise()
        .to_audio_segment(duration=1000)
        .apply_gain(headroom)
    )
    _file = Path(input_tmpdir) / "file.wav"
    audio.export(_file, format="wav")

    return audio, _file


@pytest.fixture
def playlist_config():
    """Test playlist config fixture."""
    with open(
        "tests/data/collection_playlists.yaml", mode="r", encoding="utf-8"
    ) as _file:
        return yaml.load(_file.read(), Loader=yaml.FullLoader)


@pytest.fixture(scope="session")
def rekordbox_playlist_tag():  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox playlist tag."""
    playlist_string = (
        """<NODE Name="ROOT" Type="0" Count="2">"""
        """  <NODE Name="Genres" Type="0" Count="1">"""
        """    <NODE Name="Hip Hop" Type="1" Entries="1">"""
        """      <TRACK Key="2"/>"""
        """    </NODE>"""
        """  </NODE>"""
        """  <NODE Name="My Tags" Type="0" Count="1">"""
        """    <NODE Name="Dark" Type="1" Entries="0"/>"""
        """  </NODE>"""
        """</NODE>"""
    )
    return BeautifulSoup(playlist_string, "xml").find("NODE")


@pytest.fixture(scope="session")
def rekordbox_playlist(
    rekordbox_playlist_tag,
):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox playlist object."""
    return RekordboxPlaylist(rekordbox_playlist_tag)


@pytest.fixture(scope="session")
def rekordbox_track_tag(input_tmpdir):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox track tag."""
    track_string = (
        """<TRACK AverageBpm="140.00" Comments="/* Dark */" """
        """DateAdded="2023-06-24" Genre="Dubstep" """
        """Location="file://localhost/track1.mp3" Rating="255" TrackID="1" """
        """TrackNumber="1">\n<TEMPO/>\n<POSITION_MARK/>\n</TRACK>"""
    )
    track_tag = BeautifulSoup(track_string, "xml").find("TRACK")
    test_dir = Path(input_tmpdir) / "input"
    test_dir.mkdir(exist_ok=True)
    track_name = Path(track_tag["Location"]).name
    prefix = "file://localhost" if os.name == "posix" else "file://localhost/"
    track_tag["Location"] = f"{prefix}{(test_dir / track_name).as_posix()}"
    with open(test_dir / track_name, mode="w", encoding="utf-8") as _file:
        _file.write("")

    return track_tag


@pytest.fixture()
def rekordbox_track(
    rekordbox_track_tag,
):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox track object."""
    return RekordboxTrack(rekordbox_track_tag)


@pytest.fixture(scope="session")
def rekordbox_xml(input_tmpdir):  # pylint: disable=redefined-outer-name
    """Fixture for XML file."""
    input_tmpdir = Path(input_tmpdir)
    collection = RekordboxCollection("tests/data/rekordbox.xml")
    for track in collection.get_tracks().values():
        track.set_location(input_tmpdir / track.get_location().name)
        with open(track.get_location(), mode="w", encoding="utf-8") as _file:
            _file.write("")

    return collection.serialize(output_path=input_tmpdir / "rekordbox.xml")


@pytest.fixture(scope="session")
def rekordbox_collection_tag(
    rekordbox_xml,
):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox collection tag."""
    with open(rekordbox_xml, mode="r", encoding="utf-8") as _file:
        xml = BeautifulSoup(
            _file.read(), "xml"
        )  # pylint: disable=redefined-outer-name

    return xml


@pytest.fixture(scope="session")
def rekordbox_collection(
    rekordbox_xml,
):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox collection object."""
    return RekordboxCollection(rekordbox_xml)


###############################################################################
# Pytest hooks for producing timing information for fixtures and test cases.
###############################################################################


# @pytest.hookimpl(hookwrapper=True)
# def pytest_fixture_setup(request):
#     start = time.time()
#     yield
#     print(f"[DEBUG] {request.fixturename} [fixture]={time.time() - start}")


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_setup(item):
#     start = time.time()
#     yield
#     print(f"[DEBUG] {item.listnames()[-1]} [setup]={time.time() - start}")


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_call(item):
#     start = time.time()
#     yield
#     print(f"[DEBUG] {item.listnames()[-1]} [call]={time.time() - start}")


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_teardown(item):
#     start = time.time()
#     yield
#     print(f"[DEBUG] {item.listnames()[-1]} [teardown]={time.time() - start}")

"""This module contains fixtures for DJ Tools."""

import os
from argparse import Namespace
from pathlib import Path
from unittest import mock

import pytest
import yaml
from bs4 import BeautifulSoup
from pydub import AudioSegment, generators

from djtools.configs.config import BaseConfig
from djtools.collection.config import PlaylistConfig
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_track import RekordboxTrack


@pytest.fixture
def namespace():
    """Test Namespace object fixture."""
    return Namespace(link_configs=False, log_level="INFO", version=False)


@pytest.fixture
@mock.patch("djtools.spotify.helpers.Client", mock.MagicMock())
def config():
    """Test config fixture."""
    return BaseConfig()


@pytest.fixture
def config_file_teardown():
    """Teardown config.yaml."""
    yield
    config_dir = Path(__file__).parent.parent / "src" / "djtools" / "configs"
    config_file = config_dir / "config.yaml"
    if config_file.exists():
        config_file.unlink()


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


@pytest.fixture
def playlist_config_content():
    """Test playlist config content fixture."""
    with open(
        "tests/data/collection_playlists.yaml", mode="r", encoding="utf-8"
    ) as _file:
        return _file.read()


@pytest.fixture
def playlist_config_obj(
    playlist_config,
):  # pylint: disable=redefined-outer-name
    """Test playlist config object fixture."""
    return PlaylistConfig(**playlist_config)


@pytest.fixture(scope="session")
def rekordbox_playlist_tag():  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox playlist tag."""
    playlist_string = (
        """<NODE Name="ROOT" Type="0" Count="2">\n"""
        """  <NODE Name="Genres" Type="0" Count="1">\n"""
        """    <NODE Name="Hip Hop" Type="1" Entries="1">\n"""
        """      <TRACK Key="2"/>\n"""
        """    </NODE>\n"""
        """  </NODE>\n"""
        """  <NODE Name="My Tags" Type="0" Count="1">\n"""
        """    <NODE Name="Dark" Type="1" Entries="0"/>\n"""
        """  </NODE>\n"""
        """</NODE>"""
    )
    return BeautifulSoup(playlist_string, "xml").find("NODE")


@pytest.fixture(scope="session")
def rekordbox_track_tag(input_tmpdir):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox track tag."""
    track_string = (
        """<TRACK Artist="A Tribe Called Quest" AverageBpm="86.00" """
        """Comments=" /* Gangsta */ " DateAdded="2022-06-24" Genre="Hip Hop / R&amp;B" """
        """Label="Label" Location="file://localhost/track2.mp3" """
        """Tonality="7B" Rating="0" TrackID="2" """
        """TrackNumber="2" Year="2022"/>"""
    )
    track_tag = BeautifulSoup(track_string, "xml").find("TRACK")
    test_dir = Path(input_tmpdir) / "input"
    test_dir.mkdir(exist_ok=True)
    track_name = Path(track_tag["Location"]).name
    prefix = (
        "file://localhost"
        if os.name == "posix"  # pylint: disable=no-member
        else "file://localhost/"
    )
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

    return collection.serialize(path=input_tmpdir / "rekordbox.xml")


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


@pytest.fixture(scope="session")
def rekordbox_playlist(
    rekordbox_collection,
):  # pylint: disable=redefined-outer-name
    """Fixture for Rekordbox playlist object."""
    return rekordbox_collection.get_playlists()


###############################################################################
# Pytest hooks for producing timing information for fixtures and test cases.
###############################################################################


# import time

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

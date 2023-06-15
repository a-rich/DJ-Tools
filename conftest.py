"""This module contains fixtures for DJ Tools."""
from argparse import Namespace
from pathlib import Path
import shutil
# import time
from unittest import mock
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup
import pytest

from djtools.configs.config import BaseConfig
from djtools.configs.helpers import filter_dict, pkg_cfg


@pytest.fixture
def namespace():
    """Test Namespace object fixture."""
    return Namespace(link_configs=False, log_level="INFO", version=False)


@pytest.fixture
@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.MagicMock())
def test_config():
    """Test config fixture."""
    configs = {pkg: cfg() for pkg, cfg in pkg_cfg.items() if pkg != "configs"}
    joined_config = BaseConfig(
        **{
            k: v for cfg in configs.values()
            for k, v in filter_dict(cfg).items()
        }
    )

    return joined_config


@pytest.fixture
def test_playlist_config(tmpdir):
    """Test playlist config fixture."""
    src = Path("djtools/configs/rekordbox_playlists.yaml")
    dst = tmpdir / src.name
    shutil.copyfile(str(src), str(dst))

    return dst


@pytest.fixture(scope="session")
def test_track(xml_tmpdir, xml):  # pylint: disable=redefined-outer-name
    """Test track fixture."""
    xml_tmpdir = Path(xml_tmpdir)
    test_dir = xml_tmpdir / "input"
    test_dir.mkdir()
    track = xml.find("TRACK")
    track_name = Path(track["Location"]).name
    track["Location"] = quote((test_dir / track_name).as_posix())
    with open(unquote(track["Location"]), mode="w", encoding="utf-8") as _file:
        _file.write("")

    return track


@pytest.fixture(scope="session")
def test_xml(xml_tmpdir, xml):  # pylint: disable=redefined-outer-name
    """Test XML fixture."""
    xml_tmpdir = Path(xml_tmpdir)
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        track_name = Path(track["Location"]).name
        track["Location"] = quote((xml_tmpdir / track_name).as_posix())
        with open(
            unquote(track["Location"]), mode="w", encoding="utf-8"
        ) as _file:
            _file.write("")
    xml_path = xml_tmpdir / "rekordbox.xml"
    with open(
        xml_path,
        mode="wb",
        encoding=xml.original_encoding,
    ) as _file:
        _file.write(xml.prettify("utf-8"))

    return xml_path


@pytest.fixture(scope="session")
def xml_tmpdir(tmpdir_factory):
    """Test tmpdir fixture."""
    return tmpdir_factory.mktemp("input")


@pytest.fixture(scope="session")
def xml():
    """Test XML fixture."""
    with open(
        "testing/data/rekordbox.xml", mode="r", encoding="utf-8"
    ) as _file:
        xml = BeautifulSoup(_file.read(), "xml")  # pylint: disable=redefined-outer-name

    return xml


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

import os
import shutil
# import time
from unittest import mock
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.configs.config import BaseConfig
from djtools.configs.helpers import filter_dict, pkg_cfg
from djtools.utils.helpers import MockOpen


@pytest.fixture
@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"], write_only=True).open,
)
def test_config(mock_get_spotify_client):
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
    src = "djtools/configs/rekordbox_playlists.yaml"
    dst = os.path.join(tmpdir, os.path.basename(src))
    shutil.copyfile(src, dst)

    return dst


@pytest.fixture(scope="session")
def test_track(xml_tmpdir, xml):
    test_dir = os.path.join(xml_tmpdir, "input").replace(os.sep, "/")
    os.makedirs(test_dir, exist_ok=True)
    track = xml.find("TRACK")
    track_name = os.path.basename(track["Location"])
    track["Location"] = os.path.join(test_dir, track_name).replace(os.sep, "/")
    with open(unquote(track["Location"]), mode="w", encoding="utf-8") as _file:
        _file.write("")

    return track


@pytest.fixture(scope="session")
def test_xml(xml_tmpdir, xml):
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        track_name = os.path.basename(track["Location"])
        track["Location"] = os.path.join(
            xml_tmpdir, track_name
        ).replace(os.sep, "/")
        with open(
            unquote(track["Location"]), mode="w", encoding="utf-8"
        ) as _file:
            _file.write("")
    xml_path = os.path.join(xml_tmpdir, "rekordbox.xml").replace(os.sep, "/")
    with open(
        xml_path,
        mode="wb",
        encoding=xml.original_encoding,
    ) as _file:
        _file.write(xml.prettify("utf-8"))
    
    return xml_path


@pytest.fixture(scope="session")
def xml_tmpdir(tmpdir_factory):
    return tmpdir_factory.mktemp("input")


@pytest.fixture(scope="session")
def xml():
    with open(
        "test_data/rekordbox.xml", mode="r", encoding="utf-8"
    ) as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    
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

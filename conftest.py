# import time

from bs4 import BeautifulSoup
import pytest


@pytest.fixture(scope="session")
def xml_tmpdir(tmpdir_factory):
    return tmpdir_factory.mktemp("input")


@pytest.fixture(scope="session")
def xml():
    with open(
        "src/test_data/rekordbox.xml", mode="r", encoding="utf-8"
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

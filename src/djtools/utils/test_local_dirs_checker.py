import os

import pytest
from unittest import mock

from djtools.utils.local_dirs_checker import check_local_dirs, get_local_tracks


pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize(
    "beatcloud_tracks", [[], ["test_file1", "test_file2"]]
)
@pytest.mark.parametrize(
    "local_tracks", [[], ["test_file1", "test_file2"]]
)
@mock.patch(
    "djtools.utils.local_dirs_checker.get_beatcloud_tracks",
    return_value=["test_file1", "test_file2"],
)
def test_check_local_dirs(
    tmpdir,
    test_config,
    caplog,
    beatcloud_tracks,
    local_tracks,
):
    caplog.set_level("INFO")
    test_config["CHECK_TRACK_OVERLAP_FUZZ_RATIO"] = 100
    check_dirs = []
    for dir in ["dir1", "dir2"]:
        path = os.path.join(tmpdir, dir).replace(os.sep, "/")
        os.makedirs(path)
        check_dirs.append(path)
    test_config["LOCAL_CHECK_DIRS"] = check_dirs
    for index, track in enumerate(
        local_tracks + (["some_other_file"] if local_tracks else [])
    ):
        with open(
            os.path.join(
                check_dirs[index % len(check_dirs)], f"{track}.mp3"
            ).replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ) as _file:
            _file.write("")
    ret = check_local_dirs(test_config, beatcloud_tracks)
    if local_tracks and beatcloud_tracks:
        matches = 0
        for record in caplog.records:
            if record.message.startswith("Local tracks / beatcloud matches:"):
                continue
            if any(x in record.message for x in check_dirs):
                continue
            matches += 1
            assert any(
                record.message == f"\t100: {x} | {x}" for x in local_tracks
            )
        assert matches == len(local_tracks)
    elif not local_tracks:
        assert not ret


def test_get_local_tracks(tmpdir, test_config):
    check_dirs = []
    for dir in ["dir1", "dir2"]:
        path = os.path.join(tmpdir, dir).replace(os.sep, "/")
        os.makedirs(path)
        check_dirs.append(path)
    test_config["LOCAL_CHECK_DIRS"] = check_dirs + ["nonexistent_dir"]
    beatcloud_tracks = ["test_file1.mp3", "test_file2.mp3"]
    for index, track in enumerate(beatcloud_tracks):
        with open(
            os.path.join(
                check_dirs[index % len(check_dirs)], f"{track}"
            ).replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ) as _file:
            _file.write("")
    local_dir_tracks = get_local_tracks(test_config)
    assert all(x in local_dir_tracks for x in check_dirs)
    assert len(local_dir_tracks) == len(check_dirs)


def test_get_local_tracks_no_dirs_key(test_config):
    del test_config["LOCAL_CHECK_DIRS"]
    with pytest.raises(KeyError):
        get_local_tracks(test_config)

def test_get_local_tracks_no_dirs(test_config):
    test_config["LOCAL_CHECK_DIRS"] = ""
    with pytest.raises(ValueError):
        get_local_tracks(test_config)

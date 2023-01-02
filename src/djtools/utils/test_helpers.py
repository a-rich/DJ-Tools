from datetime import datetime, timedelta
import os
from unittest import mock

import pytest

from djtools.utils.helpers import (
    catch,
    compare_tracks,
    get_beatcloud_tracks,
    get_local_tracks,
    make_dirs,
    raise_,
    upload_log,
)


pytest_plugins = [
    "test_data",
]


def test_catch():
    x = "test"
    func = lambda x: x
    assert catch(func, x) == func(x)
    func = lambda x: x/0
    ret = catch(func, x)
    assert ret is None
    handler_ret = "some string"
    handler = lambda x: handler_ret
    ret = catch(func, x, handle=handler)
    assert ret == handler_ret


@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_make_dirs(tmpdir, platform):
    with mock.patch("djtools.utils.helpers.os_name", platform):
        new_dir = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
        make_dirs(new_dir)
        assert os.path.exists(new_dir)
        new_sub_dir = os.path.join(
            tmpdir, "test_dir_2", "sub_dir"
        ).replace(os.sep, "/")
        make_dirs(new_sub_dir)
        assert os.path.exists(new_sub_dir)
        rel_dir = os.path.join(tmpdir, "relative_dir").replace(os.sep, "/")
        make_dirs(rel_dir)
        assert os.path.exists(rel_dir)



def test_raise_():
    with pytest.raises(Exception):
        raise_(Exception())


def test_upload_log(tmpdir, test_config):
    test_config["AWS_PROFILE"] = "DJ"
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    test_log = f'{now.strftime("%Y-%m-%d")}.log'
    filenames = [
        "empty.txt",
        test_log, 
        f'{one_day_ago.strftime("%Y-%m-%d")}.log',
    ]
    ctime = one_day_ago.timestamp()
    for filename in filenames:
        file_path = os.path.join(tmpdir, filename).replace(os.sep, "/")
        with open(file_path, mode="w", encoding="utf-8") as _file:
            _file.write("stuff")
        if filename != test_log: 
            os.utime(file_path, (ctime, ctime))
    upload_log(
        test_config, os.path.join(tmpdir, test_log).replace(os.sep, "/")
    )
    assert len(os.listdir(tmpdir)) == len(filenames) - 1


def test_upload_log_no_aws_profile(test_config, caplog):
    caplog.set_level("WARNING")
    test_config["AWS_PROFILE"] = ""
    ret = upload_log(test_config, "some_file.txt")
    assert ret is None
    assert (
        caplog.records[0].message == "Logs cannot be backed up without "
        "specifying the config option AWS_PROFILE"
    )


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


@pytest.mark.parametrize(
    "proc_dump",
    [
        [],
        [
            "aweeeezy/Bass/2022-12-21/track - artist.mp3",
            "aweeeezy/Techno/2022-12-21/track - artist.mp3",
        ]
    ]
)
@mock.patch("os.popen")
def test_get_beatcloud_tracks(mock_os_popen, proc_dump):
    process = mock_os_popen.return_value.__enter__.return_value
    process.read.side_effect = lambda: "\n".join(proc_dump)
    tracks = get_beatcloud_tracks()
    mock_os_popen.assert_called_once()
    assert len(tracks) == len(proc_dump)
    for track, line in zip(tracks, proc_dump):
        assert track == line


@pytest.mark.parametrize("get_spotify_tracks_flag", [True, False])
@pytest.mark.parametrize("get_local_tracks_flag", [True, False])
@pytest.mark.parametrize("beatcloud_tracks", [[], ["track - artist"]])
@mock.patch("djtools.utils.helpers.get_local_tracks", return_value={})
@mock.patch(
    "djtools.utils.helpers.get_beatcloud_tracks",
    return_value=["aweeeezy/Bass/2022-12-21/track - artist.mp3"],
)
@mock.patch("djtools.utils.helpers.get_spotify_tracks", return_value={})
def test_compare_tracks(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    mock_get_local_tracks,
    get_spotify_tracks_flag,
    get_local_tracks_flag,
    beatcloud_tracks,
    test_config,
    tmpdir,
    caplog,
):
    caplog.set_level("INFO")
    playlist_name = "playlist"
    test_config["SPOTIFY_CHECK_PLAYLISTS"] = [playlist_name]
    test_config["LOCAL_CHECK_DIRS"] = [str(tmpdir)]
    if get_spotify_tracks_flag:
        mock_get_spotify_tracks.return_value = {"playlist": ["track - artist"]}
    if get_local_tracks_flag:
        mock_get_local_tracks.return_value = {str(tmpdir): ["track - artist"]}
    ret_beatcloud_tracks, beatcloud_matches = compare_tracks(
        test_config, beatcloud_tracks
    )
    if not get_spotify_tracks_flag:
        assert caplog.records.pop(0).message == (
            "There are no Spotify tracks; make sure SPOTIFY_CHECK_PLAYLISTS "
            "has one or more keys from spotify_playlists.json"
        )
    if not get_local_tracks_flag:
        assert caplog.records.pop(0).message == (
            "There are no local tracks; make sure LOCAL_CHECK_DIRS has "
            'one or more directories containing one or more tracks'
        )
    if not beatcloud_tracks and (
        get_spotify_tracks_flag or get_local_tracks_flag
    ):
        mock_get_beatcloud_tracks.assert_called_once()
    if get_spotify_tracks_flag:
        assert caplog.records.pop(0).message == (
            "\nSpotify Playlist Tracks / Beatcloud Matches: "
            f"{len(mock_get_spotify_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{playlist_name}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
    if get_local_tracks_flag:
        assert caplog.records.pop(0).message == (
            "\nLocal Directory Tracks / Beatcloud Matches: "
            f"{len(mock_get_local_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{str(tmpdir)}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )

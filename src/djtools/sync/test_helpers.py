import os
from unittest import mock

from bs4 import BeautifulSoup
import pytest

from djtools.sync.helpers import (
    parse_sync_command, rewrite_xml, run_sync, webhook
)


pytest_plugins = [
    "test_data",
]


class MockOpen:
    builtin_open = open

    def __init__(self, user_a_path, user_b_path, handle_file):
        self.user_a_path = user_a_path
        self.user_b_path = user_b_path
        self.handle_file = handle_file

    def open(self, *args, **kwargs):
        if os.path.basename(args[0]) == self.handle_file:
            return mock.mock_open(
                read_data=f'{{"aweeeezy": "{self.user_a_path}", '
                    f'"other_user": "{self.user_b_path}"}}'
            )(*args, **kwargs)
        return self.builtin_open(*args, **kwargs)


@pytest.mark.parametrize("upload", [True, False])
@pytest.mark.parametrize(
    "include_dirs", [[], ["path/to/stuff", "path/to/things"]]
)
@pytest.mark.parametrize(
    "exclude_dirs", [[], ["path/to/stuff", "path/to/things"]]
)
@pytest.mark.parametrize("use_date_modified", [True, False])
@pytest.mark.parametrize("dryrun", [True, False])
def test_parse_sync_command(
    tmpdir,
    test_config,
    upload,
    include_dirs,
    exclude_dirs,
    use_date_modified,
    dryrun,
):
    tmpdir = str(tmpdir)
    if upload:
        test_config["UPLOAD_INCLUDE_DIRS"] = include_dirs
        test_config["UPLOAD_EXCLUDE_DIRS"] = exclude_dirs
    else:
        test_config["DOWNLOAD_INCLUDE_DIRS"] = include_dirs
        test_config["DOWNLOAD_EXCLUDE_DIRS"] = exclude_dirs
    test_config["AWS_USE_DATE_MODIFIED"] = not use_date_modified
    test_config["DRYRUN"] = dryrun
    partial_cmd = [
        "aws",
        "s3",
        "sync",
        tmpdir if upload else "s3://dj.beatcloud.com/dj/music/",
        "s3://dj.beatcloud.com/dj/music/" if upload else tmpdir,
    ]
    cmd = ""
    if include_dirs and exclude_dirs:
        # Including and excluding directories within the same "sync" command is
        # not allowed.
        with pytest.raises(ValueError):
            cmd = parse_sync_command(partial_cmd, test_config, upload)
    else:
        cmd = parse_sync_command(partial_cmd, test_config, upload)
        cmd = " ".join(cmd)
        if include_dirs:
            assert all(f"--include {x}" in cmd for x in include_dirs)
            assert "--exclude *" in cmd
        elif exclude_dirs:
            assert all(f"--exclude {x}" in cmd for x in exclude_dirs)
            assert "--include *" in cmd
        if use_date_modified:
            assert "--size-only" in cmd
        if dryrun:
            assert "--dryrun" in cmd


@mock.patch(
    "builtins.open",
    MockOpen(
        user_a_path="/Volumes/AWEEEEZY/",
        user_b_path="/Volumes/my_beat_stick/",
        handle_file="registered_users.json",
    ).open
)
def test_rewrite_xml(test_config, test_xml):
    user_a_path= "/Volumes/AWEEEEZY/"
    user_b_path= "/Volumes/my_beat_stick/"
    test_user = "aweeeezy"
    other_user = "other_user"
    test_config["USER"] = test_user
    test_config["XML_IMPORT_USER"] = other_user
    test_config["XML_PATH"] = test_xml
    other_users_xml = os.path.join(
        os.path.dirname(test_xml), f'{other_user}_rekordbox.xml'
    ).replace(os.sep, "/")
    # Create dummy "other_user" XML.
    os.rename(test_xml, other_users_xml)

    # Insert the USB path of "other_user" into all the track Locations.
    with open(other_users_xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            track["Location"] = os.path.join(
                os.path.dirname(track["Location"]),
                user_b_path.strip("/"),
                os.path.basename(track["Location"]),
            ).replace(os.sep, "/")
    
    # Write this XML back to file.
    with open(
        other_users_xml, mode="wb", encoding=soup.orignal_encoding
    ) as _file:
        _file.write(soup.prettify("utf-8"))
        
    # Rewrite XML to replace the USB path of "other_user" with that of
    # "test_user".
    rewrite_xml(test_config)

    # Assert that none of the track Location fields contain the USB path of
    # "other_user" and all of them contain that of "test_user". 
    with open(other_users_xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            assert user_a_path in track["Location"]
            assert user_b_path not in track["Location"]
            example2 = track["Location"]


def test_run_sync():
    # TODO: figure out how to test "run_sync"
    pass


def test_webhook():
    pass

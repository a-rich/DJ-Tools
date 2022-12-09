from datetime import datetime, timedelta
import os
from unittest.mock import patch

import pytest

from djtools.utils.helpers import catch, make_dirs, raise_, upload_log


pytest_plugins = [
    "test_data",
]


def test_catch():
    x = "test"
    func = lambda x: x
    # Non-exception case: "catch" returns the same thing as the function it
    # calls.
    assert catch(func, x) == func(x)
    func = lambda x: x/0
    ret = catch(func, x)
    # Exception case: "catch" returns None by default.
    assert ret is None
    handler_ret = "some string"
    handler = lambda x: handler_ret
    ret = catch(func, x, handle=handler)
    # Exception case: "catch" executes provided handler. 
    assert ret == handler_ret


@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_make_dirs(tmpdir, platform):
    with patch("djtools.utils.helpers.os_name", platform):
        new_dir = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
        make_dirs(new_dir)
        # New directory is created as expected.
        assert os.path.exists(new_dir)
        new_sub_dir = os.path.join(
            tmpdir, "test_dir_2", "sub_dir"
        ).replace(os.sep, "/")
        make_dirs(new_sub_dir)
        # New directory and sub-directory created as expected.
        assert os.path.exists(new_sub_dir)



def test_raise_():
    with pytest.raises(Exception):
        raise_(Exception())


def test_upload_log(tmpdir, test_config):
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
    # Files older than one day are removed; "empty.txt" is not removed.
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

"""Testing for the helpers module."""
from datetime import datetime, timedelta
import os
from pathlib import Path
import tempfile
from unittest import mock
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.sync.helpers import (
    parse_sync_command, rewrite_xml, run_sync, upload_log, webhook
)


@pytest.mark.parametrize("upload", [True, False])
@pytest.mark.parametrize(
    "include_dirs", [[], ["path/to/stuff", "path/to/things.mp3"]]
)
@pytest.mark.parametrize(
    "exclude_dirs", [[], ["path/to/stuff", "path/to/things.mp3"]]
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
    """Test for the parse_sync_command function."""
    tmpdir = str(tmpdir)
    if upload:
        test_config.UPLOAD_INCLUDE_DIRS = include_dirs
        test_config.UPLOAD_EXCLUDE_DIRS = exclude_dirs
    else:
        test_config.DOWNLOAD_INCLUDE_DIRS = include_dirs
        test_config.DOWNLOAD_EXCLUDE_DIRS = exclude_dirs
    test_config.AWS_USE_DATE_MODIFIED = not use_date_modified
    test_config.DRYRUN = dryrun
    partial_cmd = [
        "aws",
        "s3",
        "sync",
        tmpdir if upload else "s3://dj.beatcloud.com/dj/music/",
        "s3://dj.beatcloud.com/dj/music/" if upload else tmpdir,
    ]
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


def test_rewrite_xml(test_config, test_xml, xml):
    """Test for the rewrite_xml function."""
    user_a_path= "/Volumes/AWEEEEZY/"
    user_b_path= "/Volumes/my_beat_stick/"
    test_user = "aweeeezy"
    other_user = "other_user"
    test_config.USER = test_user
    test_config.IMPORT_USER = other_user
    test_config.XML_PATH = test_xml
    test_config.USB_PATH = Path("/Volumes/AWEEEEZY/")
    other_users_xml = Path(test_xml).parent / f"{other_user}_rekordbox.xml"
    other_users_xml.write_text(
        Path(test_xml).read_text(encoding="utf-8"), encoding="utf-8"
    )

    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        # NOTE(a-rich): `Location` attributes in the XML's `TRACK` tags always
        # have unix-style paths so paths created in Windows must be
        # interpreted `.as_posix()`.
        track["Location"] = (
            Path(track["Location"]).parent / user_b_path.strip("/") /
            "DJ Music" / Path(track["Location"]).name
        ).as_posix()

    with open(
        other_users_xml, mode="wb", encoding=xml.original_encoding
    ) as _file:
        _file.write(xml.prettify("utf-8"))

    rewrite_xml(test_config)

    with open(other_users_xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            assert user_a_path in unquote(track["Location"])
            assert user_b_path not in unquote(track["Location"])


@mock.patch("djtools.sync.helpers.Popen")
def test_run_sync(mock_popen, tmpdir):
    """Test for the run_sync function."""
    with open(Path(tmpdir) / "track.mp3", mode="w", encoding="utf-8") as _file:
        _file.write("")
    cmd = ["aws", "s3", "sync", str(tmpdir), "s3://dj.beatcloud.com/dj/music/"]
    sync_output = (
        "upload: ../../Volumes/AWEEEEZY/DJ Music/Bass/2022-12-21/track - "
            "artist.mp3 to s3://dj.beatcloud.com/dj/music/Bass/2022-12-21/"
            "track - artist.mp3\n"
        "upload: ../../Volumes/AWEEEEZY/DJ Music/Bass/2O22-12-21/other track "
            "- other artist.mp3 to s3://dj.beatcloud.com/dj/music/Bass/"
            "2O22-12-21/other track - other artist.mp3\n"
        "upload: ../../Volumes/AWEEEEZY/DJ Music/Techno/2022-12-22/last track "
            "- last artist.mp3 to s3://dj.beatcloud.com/dj/music/Techno/"
            "2022-12-22/last track - last artist.mp3"
        "\nirrelevant line"
    )
    # NOTE(a-rich): Windows does not allow opening a temporary file after it's
    # been created. The WAR is to initialize a `NamedTemporaryFile` with the
    # `delete` argument set to `False` and explicitly `.close()` the object
    # before calling `open()` on it.
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write(sync_output)
        tmp_file.seek(0)
        tmp_file.close()
        with open(tmp_file.name, encoding="utf-8") as tmp_file:
            process = mock_popen.return_value.__enter__.return_value
            process.stdout = tmp_file
            process.wait.return_value = 0
            ret = run_sync(cmd)
    expected = (
        "Bass/2022-12-21: 1\n\ttrack - artist.mp3\nBass/2O22-12-21: 1\n\tother"
        " track - other artist.mp3\nTechno/2022-12-22: 1\n\tlast track - last "
        "artist.mp3\n"
    )
    assert ret == expected


@mock.patch("djtools.sync.helpers.Popen")
def test_run_sync_handles_return_code(mock_popen, tmpdir, caplog):
    """Test for the run_sync function."""
    caplog.set_level("CRITICAL")
    # NOTE(a-rich): subprocess calls to `awscli` need to have unix-style path
    # arguments.
    cmd = [
        "aws",
        "s3",
        "sync",
        Path(tmpdir).as_posix(),
        "s3://dj.beatcloud.com/dj/music/",
    ]
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write("")
        tmp_file.seek(0)
        tmp_file.close()
        with open(tmp_file.name, encoding="utf-8") as tmp_file:
            process = mock_popen.return_value.__enter__.return_value
            process.stdout = tmp_file
            process.wait.return_value = 1
            msg = (
                f"Failure while syncing: Command '{' '.join(cmd)}' returned "
                f"non-zero exit status {process.wait.return_value}."
            )
            with pytest.raises(Exception, match=msg):
                run_sync(cmd)
    assert caplog.records[0].message == msg


@mock.patch("subprocess.Popen.wait", mock.Mock())
def test_upload_log(tmpdir, test_config):
    """Test for the upload_log function."""
    test_config.AWS_PROFILE = "DJ"
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
        file_path = Path(tmpdir) / filename
        with open(file_path, mode="w", encoding="utf-8") as _file:
            _file.write("stuff")
        if filename != test_log:
            os.utime(file_path, (ctime, ctime))
    upload_log(test_config, Path(tmpdir) / test_log)
    assert len(list(Path(tmpdir).iterdir())) == len(filenames) - 1


def test_upload_log_no_aws_profile(test_config, caplog):
    """Test for the upload_log function."""
    caplog.set_level("WARNING")
    test_config.AWS_PROFILE = ""
    upload_log(test_config, "some_file.txt")
    assert (
        caplog.records[0].message == "Logs cannot be backed up without "
        "specifying the config option AWS_PROFILE"
    )


@pytest.mark.parametrize(
    "content",
    [
        "*",
        "*"*2001,
        "*"*1900 + "\n" + "*"*99,
        "*"*1900 + "\n" + "*"*100,
    ],
)
@mock.patch("requests.post", side_effect=lambda *args, **kwargs: None)
def test_webhook(mock_post, content):
    """Test for the webhook function."""
    url = "https://discord.com/api/webhooks/some-id/"
    content_size_limit = 2000
    posts = len(content) // content_size_limit
    remainder = len(content) % content_size_limit
    posts = posts + 1 if remainder else posts
    webhook(url=url, content_size_limit=content_size_limit, content=content)
    assert mock_post.call_count == max(posts, len(content.split("\n")))


def test_webhook_no_content(caplog):
    """Test for the webhook function."""
    caplog.set_level("INFO")
    url = "https://discord.com/api/webhooks/some-id/"
    content = ""
    webhook(url=url, content=content)
    assert caplog.records[0].message == "There's no content"

from argparse import Namespace
import os
from unittest import mock

import pytest

from djtools.utils.config import arg_parse, build_config, parse_json
from test_data import MockOpen


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.json"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("other_user", "/other/USB/"),
    ).open,
)
def test_build_config(tmpdir):
    with mock.patch(
        "argparse.ArgumentParser.parse_args",
    ) as mock_parse_args:
        config_path = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
        mock_parse_args.return_value = Namespace(
            link_configs=config_path, log_level="INFO"
        )
        config = build_config()
    assert isinstance(config, dict)


@mock.patch("builtins.open", MockOpen(
    files=["config.json"],
    content='{"json_valid": false,}',
).open)
@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        link_configs="", log_level="INFO"
   )
)
def test_build_config_invalid_config_json(mock_parse_args, caplog):
    caplog.set_level("CRITICAL")
    with pytest.raises(Exception) as exc:
        config = build_config()
    assert 'Error reading "config.json"' in caplog.records[0].message


@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        aws_profile="", link_configs="", log_level="INFO", download_xml=True
   )
)
def test_build_config_aws_profile_not_set(mock_parse_args, caplog):
    caplog.set_level("CRITICAL")
    with pytest.raises(ValueError):
        config = build_config()
    assert (
        caplog.records[0].message == "Config must include AWS_PROFILE if "
        "performing sync operations"
    )


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.json"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("other_user", "/other/USB/"),
    ).open,
)
@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        aws_profile="DJ",
        link_configs="",
        log_level="INFO",
        upload_music=True,
        discord_url="",
   )
)
def test_build_config_no_discord_url(mock_parse_args, caplog):
    caplog.set_level("WARNING")
    config = build_config()
    assert (
        caplog.records[0].message == "DISCORD_URL is not configured...set "
        'this for "new music" discord messages!'
    )


@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        aws_profile="DJ",
        link_configs="",
        log_level="INFO",
        upload_include_dirs=["stuff"],
        upload_exclude_dirs=["stuff"],
   )
)
def test_build_config_mutually_exclusive_include_exclude_dirs(
    mock_parse_args, caplog
):
    caplog.set_level("CRITICAL")
    with pytest.raises(ValueError):
        config = build_config()
    assert (
        caplog.records[0].message == "Config must neither contain (a) both "
        "UPLOAD_INCLUDE_DIRS and UPLOAD_EXCLUDE_DIRS or (b) both "
        "DOWNLOAD_INCLUDE_DIRS and DOWNLOAD_EXCLUDE_DIRS"
    )


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.json"],
        user_a=("aweeeezy\"", "/Volumes/AWEEEEZY/"),
        user_b=("other_user", "/other/USB/"),
    ).open,
)
@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        link_configs="", log_level="INFO"
   )
)
def test_build_config_invalid_registered_users_json(mock_parse_args, caplog):
    caplog.set_level("CRITICAL")
    with pytest.raises(Exception) as exc:
        config = build_config()
    assert 'Error reading "registered_users.json"' in caplog.records[0].message

@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.json"]).open,
)
@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        link_configs="", log_level="INFO"
   )
)
@mock.patch("os.path.exists", return_value=False)
def test_build_config_missing_registered_users_json(
    mock_parse_args, mock_path_exists, caplog
):
    caplog.set_level("WARNING")
    config = build_config()
    assert caplog.records[0].message == "No registered users!"


@mock.patch(
    "argparse.ArgumentParser.parse_args",
    return_value=Namespace(
        aws_profile="DJ",
        download_xml=True,
        xml_import_user="",
        link_configs="",
        log_level="INFO",
   )
)
def test_build_config_missing_registered_user(mock_parse_args):
    with pytest.raises(
        ValueError,
        match='Unable to import from XML of unregistered XML_IMPORT_USER ""'
    ):
        config = build_config()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs(mock_parse_args, tmpdir):
    config_path = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
    mock_parse_args.return_value = Namespace(
        link_configs=config_path, log_level="INFO"
    )
    args = arg_parse()
    assert os.path.islink(config_path)


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_not_exist(mock_parse_args, tmpdir):
    link_path = str(tmpdir)
    mock_parse_args.return_value = Namespace(
        link_configs=link_path, log_level="INFO"
    )
    with pytest.raises(
        ValueError,
        match=f'{link_path} must be a directory that does not already exist',
    ):
        args = arg_parse()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_already_exists(mock_parse_args):
    link_path = "/nonexistent/path"
    mock_parse_args.return_value = Namespace(
        link_configs=link_path, log_level="INFO"
    )
    with pytest.raises(
        ValueError,
        match=f"{os.path.dirname(link_path)} must be a directory that "
            "already exists",
    ):
        args = arg_parse()


def test_arg_parse_parse_json_valid():
    json_string = '[{"name": "stuff"}]'
    json_obj = parse_json(json_string)
    assert isinstance(json_obj, list)


def test_arg_parse_parse_json_invalid():
    json_string = '[{"name": "stuff",}]'
    with pytest.raises(ValueError):
        json_obj = parse_json(json_string)

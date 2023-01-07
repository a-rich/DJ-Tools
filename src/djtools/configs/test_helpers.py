from argparse import Namespace
import os
from unittest import mock

import pytest

from djtools.configs.helpers import arg_parse, build_config, parse_yaml
from test_data import MockOpen


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs(mock_parse_args, tmpdir):
    config_path = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
    mock_parse_args.return_value = Namespace(
        link_configs=config_path, log_level="INFO"
    )
    args = arg_parse()
    assert os.path.islink(config_path)


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_exist(mock_parse_args, tmpdir):
    link_path = os.path.join(
        str(tmpdir), "new_dir", "link_dir"
    ).replace(os.sep, "/")
    mock_parse_args.return_value = Namespace(
        link_configs=link_path, log_level="INFO"
    )
    args = arg_parse()
    assert os.path.exists(link_path)
    assert os.path.islink(link_path)


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


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.yaml"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("other_user", "/other/USB/"),
    ).open,
)
def test_build_config(mock_get_spotify_client, tmpdir):
    with mock.patch(
        "argparse.ArgumentParser.parse_args",
    ) as mock_parse_args:
        mock_parse_args.return_value = Namespace(
            link_configs="", log_level="INFO"
        )
        config = build_config()
    assert isinstance(config, dict)


@mock.patch("builtins.open", MockOpen(
    files=["config.yaml"],
    content="yaml_valid: {false",
).open)
def test_build_config_invalid_config_yaml(caplog):
    caplog.set_level("CRITICAL")
    with pytest.raises(RuntimeError) as exc:
        config = build_config()
    assert 'Error reading "config.yaml"' in caplog.records[0].message


@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml", "config.yaml"]).open
)
@mock.patch("argparse.ArgumentParser.parse_args")
def test_build_config_no_config_yaml(mock_parse_args):
    mock_parse_args.return_value = Namespace(
        link_configs="", log_level="INFO"
    )
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "configs"
    ).replace(os.sep, "/")
    config_file = os.path.join(config_dir, "config.yaml").replace(os.sep, "/")
    with mock.patch("os.path.exists", return_value=False):
        assert not os.path.exists(config_file)
        config = build_config()
    assert os.path.exists(config_file)


def test_parse_yaml():
    yaml_string = "name:\n - stuff"
    yaml_obj = parse_yaml(yaml_string)
    assert isinstance(yaml_obj, dict)
    assert isinstance(yaml_obj["name"], list)


def test_parse_yaml_invalid():
    yaml_string = "name:\n\t - stuff"
    with pytest.raises(ValueError):
        yaml_obj = parse_yaml(yaml_string)

"""Testing for the helpers module."""
from argparse import Namespace
from pathlib import Path
import re
from typing import List
from unittest import mock

import pytest

from djtools.configs.helpers import (
    arg_parse,
    BaseConfig,
    build_config,
    convert_to_paths,
    filter_dict,
    parse_yaml,
    pkg_cfg,
)
from djtools.utils.helpers import MockOpen


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs(mock_parse_args, tmpdir):
    """Test for the arg_parse function."""
    config_path = Path(tmpdir) / "test_dir"
    mock_parse_args.return_value = Namespace(
        link_configs=config_path, log_level="INFO"
    )
    arg_parse()
    assert config_path.is_symlink()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_exist(mock_parse_args, tmpdir):
    """Test for the arg_parse function."""
    link_path = Path(tmpdir) / "new_dir" / "link_dir"
    mock_parse_args.return_value = Namespace(
        link_configs=link_path, log_level="INFO"
    )
    arg_parse()
    assert link_path.exists()
    assert link_path.is_symlink()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_not_exist(mock_parse_args, tmpdir):
    """Test for the arg_parse function."""
    link_path = str(tmpdir)
    mock_parse_args.return_value = Namespace(
        link_configs=link_path, log_level="INFO"
    )
    with pytest.raises(
        ValueError,
        # NOTE(a-rich): WindowsPath needs to be escaped for `\` characters to
        # appear in the `match` argument.
        match=re.escape(
            f'{link_path} must be a directory that does not already exist'
        ),
    ):
        arg_parse()


@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.Mock())
def test_build_config():
    """Test for the build_config function."""
    with mock.patch(
        "argparse.ArgumentParser.parse_args",
    ) as mock_parse_args:
        mock_parse_args.return_value = Namespace(
            link_configs="", log_level="INFO"
        )
        config = build_config()
    assert isinstance(config, BaseConfig)


@mock.patch("builtins.open", MockOpen(
    files=["config.yaml"],
    content="yaml_valid: {false",
).open)
def test_build_config_invalid_config_yaml(caplog):
    """Test for the build_config function."""
    caplog.set_level("CRITICAL")
    with pytest.raises(RuntimeError):
        build_config()
    assert 'Error reading "config.yaml"' in caplog.records[0].message


@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.Mock())
@mock.patch("argparse.ArgumentParser.parse_args")
def test_build_config_no_config_yaml(mock_parse_args):
    """Test for the build_config function."""
    mock_parse_args.return_value = Namespace(
        link_configs="", log_level="INFO"
    )
    config_dir = Path(__file__).parent.parent / "configs"
    config_file = config_dir / "config.yaml"
    with mock.patch.object(Path, "exists", return_value=False):
        assert not config_file.exists()
        build_config()
    assert config_file.exists()


@pytest.mark.parametrize("paths", ["path", ["path1", "path2"]])
def test_convert_to_paths(paths):
    """Test for the convert_to_paths function."""
    paths = convert_to_paths(paths)
    if isinstance(paths, List):
        for path in paths:
            assert isinstance(path, Path)
    else:
        assert isinstance(paths, Path)


@pytest.mark.parametrize("config", pkg_cfg.values())
@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.Mock())
def test_filter_dict(config):
    """Test for the filter_dict function."""
    super_config = BaseConfig()
    sub_config = config(**dict(super_config))
    result = filter_dict(sub_config)
    super_keys = set(super_config.dict())
    sub_keys = set(sub_config.dict())
    result_keys = set(result)
    assert len(result_keys) + len(super_keys) == len(sub_keys)
    assert result_keys.union(super_keys) == sub_keys
    assert sub_keys.difference(result_keys) == super_keys
    assert sub_keys.difference(super_keys) == result_keys


def test_parse_yaml():
    """Test for the parse_yaml function."""
    yaml_string = "name:\n - stuff"
    yaml_obj = parse_yaml(yaml_string)
    assert isinstance(yaml_obj, dict)
    assert isinstance(yaml_obj["name"], list)


def test_parse_yaml_invalid():
    """Test for the parse_yaml function."""
    yaml_string = "name:\n\t - stuff"
    with pytest.raises(ValueError):
        parse_yaml(yaml_string)

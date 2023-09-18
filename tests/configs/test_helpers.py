"""Testing for the helpers module."""
from pathlib import Path
import re
from unittest import mock

import pytest

from djtools.configs.helpers import (
    arg_parse,
    BaseConfig,
    build_config,
    filter_dict,
    PKG_CFG,
)
from djtools.version import get_version

from ..test_utils import MockOpen


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs(mock_parse_args, tmpdir, namespace):
    """Test for the arg_parse function."""
    config_path = Path(tmpdir) / "test_dir"
    namespace.link_configs = config_path
    mock_parse_args.return_value = namespace
    arg_parse()
    assert config_path.is_symlink()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_exist(
    mock_parse_args, tmpdir, namespace
):
    """Test for the arg_parse function."""
    config_path = Path(tmpdir) / "new_dir" / "link_dir"
    namespace.link_configs = config_path
    mock_parse_args.return_value = namespace
    arg_parse()
    assert config_path.exists()
    assert config_path.is_symlink()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_arg_parse_links_configs_dir_does_not_exist(
    mock_parse_args, tmpdir, namespace
):
    """Test for the arg_parse function."""
    config_path = str(tmpdir)
    namespace.link_configs = config_path
    mock_parse_args.return_value = namespace
    with pytest.raises(
        ValueError,
        # NOTE(a-rich): WindowsPath needs to be escaped for `\` characters to
        # appear in the `match` argument.
        match=re.escape(
            f'{config_path} must be a directory that does not already exist'
        ),
    ):
        arg_parse()


@mock.patch("djtools.spotify.helpers.get_spotify_client", mock.Mock())
def test_build_config(namespace):
    """Test for the build_config function."""
    with mock.patch(
        "argparse.ArgumentParser.parse_args",
    ) as mock_parse_args:
        mock_parse_args.return_value = namespace
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
def test_build_config_no_config_yaml(mock_parse_args, namespace):
    """Test for the build_config function."""
    mock_parse_args.return_value = namespace
    config_dir = Path(__file__).parent.parent.parent / "djtools" / "configs"
    config_file = config_dir / "config.yaml"
    with mock.patch.object(Path, "exists", return_value=False):
        assert not config_file.exists()
        build_config()
    assert config_file.exists()


@mock.patch("argparse.ArgumentParser.parse_args")
def test_build_config_version(mock_parse_args, namespace, capsys):
    """Test for the build_config function."""
    namespace.version = True
    mock_parse_args.return_value = namespace
    with pytest.raises(SystemExit):
        build_config()
    assert capsys.readouterr().out == f"{get_version()}\n"


@pytest.mark.parametrize("config", PKG_CFG.values())
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


@mock.patch("builtins.open", MockOpen(
    files=["config.yaml"],
    content="sync:\n  UPLOAD_EXCLUDE_DIRS:\n    - some/path",
).open)
def test_overridding_list():
    """Test for the arg_parse function."""
    with mock.patch(
        "sys.argv", ["__main__.py", "sync", "--upload-exclude-dirs", ""]
    ):
        parse_args = arg_parse()
    assert parse_args["upload_exclude_dirs"] == []

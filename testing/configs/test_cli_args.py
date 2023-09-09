"""Testing for the cli_args module."""
from pathlib import Path
from typing import List
from unittest import mock

import pytest

from djtools.configs.cli_args import (
    convert_to_paths, get_arg_parser, parse_json
)
from djtools.configs.helpers import build_config


@pytest.mark.parametrize("paths", ["path", ["path1", "path2"]])
def test_convert_to_paths(paths):
    """Test for the convert_to_paths function."""
    paths = convert_to_paths(paths)
    if isinstance(paths, List):
        for path in paths:
            assert isinstance(path, Path)
    else:
        assert isinstance(paths, Path)


def test_get_arg_parser_arg_for_every_field(namespace):
    """Test the get_arg_parser function."""
    # Get CLI args.
    parser = get_arg_parser()
    args_set = {
        arg
        for args in [
            ["collection", "--collection-playlists"],
            ["spotify", "--spotify-playlists"],
            ["sync", "--upload-collection"],
            ["utils", "--normalize-audio"],
        ]
        for arg in parser.parse_args(args).__dict__.keys()
    }

    # Get config options.
    with mock.patch(
        "argparse.ArgumentParser.parse_args",
    ) as mock_parse_args:
        mock_parse_args.return_value = namespace
        config = build_config()  # pylint: disable=duplicate-code
    config_set = {key.lower() for key in dict(config).keys()}

    # Test that the only CLI exclusive args are linking configs and displaying
    # the version.
    cli_only = args_set.difference(config_set)
    expected_cli_only = {'link_configs', 'version'}
    assert cli_only == expected_cli_only, (
        f"Expected CLI args to be {expected_cli_only} but got {cli_only}"
    )

    # Test that every config option has a corresponding CLI arg.
    config_only = config_set.difference(args_set)
    assert config_only == set(), (
        "Expected a CLI arg for every config option but these were missing:" \
        f"\n{config_only}"
    )


def test_parse_json():
    """Test for the parse_json function."""
    json_string = '{"name": ["stuff"]}'
    json_obj = parse_json(json_string)
    assert isinstance(json_obj, dict)
    assert isinstance(json_obj["name"], list)


def test_parse_json_invalid():
    """Test for the parse_json function."""
    json_string = '{"name": {"stuff"}}'
    with pytest.raises(ValueError):
        parse_json(json_string)

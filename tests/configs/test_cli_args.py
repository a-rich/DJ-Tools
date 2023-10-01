"""Testing for the cli_args module."""
from pathlib import Path
from typing import List

import pytest

from djtools.configs.cli_args import (
    _convert_to_paths,
    get_arg_parser,
    NonEmptyListElementAction,
    _parse_json,
)


@pytest.mark.parametrize("paths", ["path", ["path1", "path2"]])
def test_convert_to_paths(paths):
    """Test for the convert_to_paths function."""
    paths = _convert_to_paths(paths)
    if isinstance(paths, List):
        for path in paths:
            assert isinstance(path, Path)
    else:
        assert isinstance(paths, Path)


def test_get_arg_parser_arg_for_every_field(config):
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
    config_set = {key.lower() for key in dict(config).keys()}

    # Test that the only CLI exclusive args are linking configs and displaying
    # the version.
    cli_only = args_set.difference(config_set)
    expected_cli_only = {"link_configs", "version"}
    assert (
        cli_only == expected_cli_only
    ), f"Expected CLI args to be {expected_cli_only} but got {cli_only}"

    # Test that every config option has a corresponding CLI arg.
    config_only = config_set.difference(args_set)
    assert config_only == set(), (
        "Expected a CLI arg for every config option but these were missing:"
        f"\n{config_only}"
    )


def test_non_empty_list_element_action(namespace):
    """Test for the NonEmptyListElementAction class."""
    namespace.local_dirs = ["first"]
    parser = get_arg_parser()
    action = NonEmptyListElementAction(option_strings=None, dest="local_dirs")
    action(parser, namespace, values=[None, "second"])
    assert namespace.local_dirs == ["first", "second"]


def test_parse_json():
    """Test for the parse_json function."""
    json_string = '{"name": ["stuff"]}'
    json_obj = _parse_json(json_string)
    assert isinstance(json_obj, dict)
    assert isinstance(json_obj["name"], list)


def test_parse_json_invalid():
    """Test for the parse_json function."""
    json_string = '{"name": {"stuff"}}'
    with pytest.raises(ValueError):
        _parse_json(json_string)

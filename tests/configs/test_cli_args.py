"""Testing for the cli_args module."""

from pathlib import Path
from typing import List

import pytest
from pydantic import BaseModel

from djtools.configs.cli_args import (
    _convert_to_paths,
    _parse_json,
    _parse_trim_initial_silence,
    get_arg_parser,
    NonEmptyListElementAction,
)
from djtools.utils.config import TrimInitialSilenceMode


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
    config_set = set()
    for field_name, field_info in config.model_fields.items():
        if isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        ):
            sub_model = getattr(config, field_name)
            config_set.update(list(sub_model.model_fields))
            continue

        config_set.add(field_name)

    # Test that the only CLI exclusive args are linking configs and displaying
    # the version.
    cli_only = args_set.difference(config_set)
    expected_cli_only = {"link_configs", "version"}
    assert (
        cli_only == expected_cli_only
    ), f"Expected CLI args to be {expected_cli_only} but got {cli_only}"

    # Test that every config option has a corresponding CLI arg.
    config_only = config_set.difference(args_set)

    # NOTE: playlist_config is the only BaseConfig attribute that doesn't have
    # a corresponding CLI arg. This is because the CollectionConfig preloads
    # the user's collection playlists.
    assert config_only == {"playlist_config"}, (
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


def test_parse_trim_initial_silence_int():
    """Test for the _parse_trim_initial_silence function."""
    arg = "1"
    assert isinstance(arg, str)
    result = _parse_trim_initial_silence(arg)
    assert isinstance(result, int)
    assert result == 1


def test_parse_trim_initial_silence_str():
    """Test for the _parse_trim_initial_silence function."""
    arg = TrimInitialSilenceMode.AUTO
    assert isinstance(arg, TrimInitialSilenceMode)
    result = _parse_trim_initial_silence(arg)
    assert isinstance(result, TrimInitialSilenceMode)
    assert result == TrimInitialSilenceMode.AUTO


def test_parse_trim_initial_silence_invalid_str():
    """Test for the _parse_trim_initial_silence function."""
    arg = "stuff"
    with pytest.raises(
        ValueError,
        match=(
            '--trim-initial-silence must be either "auto", "smart", or an '
            "integer."
        ),
    ):
        _parse_trim_initial_silence(arg)

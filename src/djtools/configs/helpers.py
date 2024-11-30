"""This module is responsible for building this library's configuration objects
using config.yaml. If command-line arguments are provided, this module
overrides the corresponding configuration options with these arguments.
"""

import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, ValidationError

from djtools.configs.cli_args import get_arg_parser
from djtools.configs.config import BaseConfig
from djtools.utils.helpers import make_path
from djtools.version import get_version


logger = logging.getLogger(__name__)


class InvalidConfigYaml(Exception):
    """Exception for invalid config."""


class ConfigLoadFailure(Exception):
    """Exception for failing to load config."""


@make_path
def build_config(
    config_file: Path = Path(__file__).parent / "config.yaml",
) -> BaseConfig:
    """This function loads configurations for the library.

    Configurations are loaded from config.yaml. If command-line arguments are
    provided, these override the configuration options set in config.yaml.

    Args:
        config_file: Optional path to a config.yaml.

    Raises:
        RuntimeError: config.yaml must be a valid YAML.

    Returns:
        Global configuration object.
    """
    # Create a default config if one doesn't already exist.
    if not config_file.exists():
        with open(config_file, mode="w", encoding="utf-8") as _file:
            yaml.dump(BaseConfig().model_dump(), _file)

    # Load the config.
    try:
        with open(config_file, mode="r", encoding="utf-8") as _file:
            config_data = yaml.load(_file, Loader=yaml.FullLoader) or {}
        config = BaseConfig(**config_data)
    except ValidationError as exc:
        msg = f"Failed to load config file {config_file}: {exc}"
        logger.critical(msg)
        raise InvalidConfigYaml(msg) from exc
    except Exception as exc:
        msg = f"Error reading config file {config_file}: {exc}"
        logger.critical(msg)
        raise ConfigLoadFailure(msg) from exc

    entry_frame_filename = inspect.stack()[-1][1]
    valid_filenames = (
        str(Path("bin") / "djtools"),  # Unix djtools.
        str(Path("bin") / "pytest"),  # Unix pytest.
        str(Path("lib") / "runpy.py"),  # Windows Python<=3.10.
        "<frozen runpy>",  # Windows Python>=3.11.
    )

    # Only get CLI arguments if calling djtools as a CLI.
    if entry_frame_filename.endswith(valid_filenames):
        args = {
            k: v for k, v in _arg_parse().items() if v or isinstance(v, list)
        }
        logger.info(f"Args: {args}")
        config = _update_config_with_cli_args(config, args)

    return config


def _arg_parse() -> Dict:
    """This function parses command-line arguments.

    It also sets the log level and symlinks a user-provided directory to the
    library's configs folder via the --link-configs argument.

    Returns:
        Dictionary of command-line arguments.
    """
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    if args.log_level:
        logger.setLevel(args.log_level)

    if args.version:
        print(get_version())
        sys.exit()

    logger.info(get_version())

    if args.link_configs:
        args.link_configs = Path(args.link_configs)
        if args.link_configs.exists():
            msg = (
                f"{args.link_configs} must be a directory that does not "
                "already exist"
            )
            logger.error(msg)
            raise ValueError(msg)
        parent_dir = args.link_configs.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
        args.link_configs.symlink_to(
            Path(__file__).parent, target_is_directory=True
        )

    return vars(args)


def _update_config_with_cli_args(
    config: BaseConfig, cli_args: Dict[str, Any]
) -> BaseConfig:
    """
    Update the BaseConfig object with CLI arguments.

    Args:
        config: The BaseConfig object.
        cli_args: CLI arguments.

    Returns:
        The updated BaseConfig object.
    """
    updated_data = config.model_dump()

    for key, value in cli_args.items():
        for field_name, field_info in config.__fields__.items():
            if (
                isinstance(field_info.annotation, type) and
                issubclass(field_info.annotation, BaseModel)
            ):
                sub_model = getattr(config, field_name)

                if key in sub_model.__fields__:
                    sub_model_data = sub_model.model_dump()
                    sub_model_data[key] = value
                    updated_data[field_name] = sub_model.__class__(
                        **sub_model_data
                    ).model_dump()
                    break

            elif key in config.__fields__:
                updated_data[key] = value

    return config.__class__(**updated_data)

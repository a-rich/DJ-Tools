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
from pydantic import BaseModel

from djtools.configs.cli_args import get_arg_parser
from djtools.configs.config import BaseConfig
from djtools.utils.helpers import make_path
from djtools.version import get_version

logger = logging.getLogger(__name__)


class InvalidConfigYamlError(Exception):
    """Exception for invalid config."""


class ConfigLoadError(Exception):
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
    except Exception as exc:
        msg = f"Error reading config file {config_file}: {exc}"
        logger.critical(msg)
        raise ConfigLoadError(msg) from exc

    entry_frame_filename = inspect.stack()[-1][1]
    valid_filenames = (
        str(Path("bin") / "djtools"),  # Unix djtools.
        str(Path("bin") / "pytest"),  # Unix pytest.
        str(Path("lib") / "runpy.py"),  # Windows Python<=3.10.
        "<frozen runpy>",  # Windows Python>=3.11.
    )

    # Only get CLI arguments if calling djtools as a CLI.
    if entry_frame_filename.endswith(valid_filenames):
        cli_args = {
            k: v for k, v in _arg_parse().items() if v or isinstance(v, list)
        }
        logger.info(f"Args: {cli_args}")
        config = _update_config_with_cli_args(config, cli_args)

    return config


def _arg_parse() -> Dict:
    """This function parses command-line arguments.

    It also sets the log level and symlinks a user-provided directory to the
    library's configs folder via the --link-configs argument.

    Returns:
        Dictionary of command-line arguments.
    """
    arg_parser = get_arg_parser()
    cli_args = arg_parser.parse_args()

    if cli_args.log_level:
        logger.setLevel(cli_args.log_level)

    if cli_args.version:
        print(get_version())
        sys.exit()

    logger.info(get_version())

    if cli_args.link_configs:
        cli_args.link_configs = Path(cli_args.link_configs)
        if cli_args.link_configs.exists():
            msg = (
                f"{cli_args.link_configs} must be a directory that does not "
                "already exist"
            )
            logger.error(msg)
            raise ValueError(msg)
        parent_dir = cli_args.link_configs.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
        cli_args.link_configs.symlink_to(
            Path(__file__).parent, target_is_directory=True
        )

    return vars(cli_args)


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

    for field_name, field_info in config.model_fields.items():
        if field_name in cli_args:
            updated_data[field_name] = cli_args[field_name]
        elif isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        ):
            sub_model = getattr(config, field_name)
            sub_model_data = sub_model.model_dump()

            sub_model_args = {
                key: value
                for key, value in cli_args.items()
                if key in sub_model.model_fields
            }

            if sub_model_args:
                sub_model_data.update(sub_model_args)
                updated_data[field_name] = sub_model.__class__(
                    **sub_model_data
                ).model_dump()

    updated_config = config.__class__(**updated_data)

    return updated_config

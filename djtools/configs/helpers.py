"""This module is responsible for building this library's configuration objects
using config.yaml. If command-line arguments are provided, this module
overrides the corresponding configuration options with these arguments.
"""
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union

import yaml

from djtools.collection.config import CollectionConfig
from djtools.configs.cli_args import get_arg_parser
from djtools.configs.config import BaseConfig
from djtools.spotify.config import SpotifyConfig
from djtools.sync.config import SyncConfig
from djtools.utils.config import UtilsConfig
from djtools.utils.helpers import make_path
from djtools.version import __version__


logger = logging.getLogger(__name__)

PKG_CFG = {
    "collection": CollectionConfig,
    "configs": BaseConfig,
    "spotify": SpotifyConfig,
    "sync": SyncConfig,
    "utils": UtilsConfig,
}


def arg_parse() -> Dict:
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
        print(__version__)
        sys.exit()

    logger.info(__version__)

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


def filter_dict(
    sub_config: Union[
        CollectionConfig, SpotifyConfig, SyncConfig, UtilsConfig
    ],
) -> Dict[Any, Any]:
    """Filters out the superclass key: value pairs of a subclass.

    Args:
        sub_config: Instance of any subclass of BaseConfig.

    Returns:
        Dictionary containing just the keys unique to "sub_config".
    """
    super_keys = set(BaseConfig.__fields__)
    return {
        k: v for k, v in sub_config.dict().items() if k not in super_keys
    }


@make_path
def build_config(config_file: Optional[Path] = None) -> BaseConfig:
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
    # Load "config.yaml".
    if not config_file:
        config_file = Path(__file__).parent / "config.yaml"
    if config_file.exists():
        try:
            with open(config_file, mode="r", encoding="utf-8") as _file:
                config = yaml.load(_file, Loader=yaml.FullLoader) or {}
        except Exception as exc:
            msg = f'Error reading "config.yaml": {exc}'
            logger.critical(msg)
            raise RuntimeError(msg) from Exception
    else:
        config = {}
        base_config_fields = BaseConfig.__fields__
        initial_config = {
            pkg: {
                k: v.default for k, v in cfg.__fields__.items()
                if pkg == "configs" or k not in base_config_fields
            }
            for pkg, cfg in PKG_CFG.items()
        }
        with open(config_file, mode="w", encoding="utf-8") as _file:
            yaml.dump(initial_config, _file)

    # Update config using command-line arguments.
    args = {
        k.upper(): v for k, v in arg_parse().items()
        if v or isinstance(v, list)
    }
    if args:
        logger.info(f"Args: {args}")
        args_set = set(args)
        for pkg, cfg_class in PKG_CFG.items():
            args_intersection = set(cfg_class.__fields__).intersection(args_set)
            if args_intersection:
                args_subset = {
                    k: v for k, v in args.items() if k in args_intersection
                }
                if pkg in config:
                    config[pkg].update(args_subset)
                else:
                    config[pkg] = args_subset

    # Instantiate Pydantic models.
    base_cfg_options = config["configs"] if config else {}
    configs = {
        pkg: cfg(**{**base_cfg_options, **config.get(pkg, {})})
        for pkg, cfg in PKG_CFG.items() if pkg != "configs"
    }
    joined_config = BaseConfig(
        **base_cfg_options,
        **{
            k: v for cfg in configs.values()
            for k, v in filter_dict(cfg).items()
        }
    )

    return joined_config

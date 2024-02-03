"""The `configs` package contains modules:
    * `cli_args`: module for handling parsing command-line arguments
    * `config`: the base configuration object containing attributes for options
        which either do not apply to any package in particular or else apply to
        multiple packages
    * `helpers`: contains functions for building configuration objects and
        parsing command-line arguments
"""

from djtools.configs.helpers import build_config


__all__ = ("build_config",)

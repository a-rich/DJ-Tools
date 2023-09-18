"""This module contains the base configuration object. All the attributes of
this configuration object either don't apply to any particular package or they
apply to multiple packages. The attributes of this configuration object
correspond with the "configs" key of config.yaml."""
import inspect
import logging
from typing_extensions import Literal

from pydantic import BaseModel, Extra, NonNegativeInt


logger = logging.getLogger(__name__)


class BaseConfig(BaseModel, extra=Extra.allow):
    """Base configuration object used across the whole library."""

    LOG_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    VERBOSITY: NonNegativeInt = 0

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super().__init__(*args, **kwargs)
        logger.info(repr(self))
        if type(self) is not BaseConfig:  # pylint: disable=unidiomatic-typecheck
            return

    def __repr__(self):
        super_keys = set(BaseConfig.__fields__)
        ret = f"{self.__class__.__name__}("

        # Inspect the stack to determine if the BaseConfig is being displayed
        # as part of the CLI's execution or otherwise.
        stack = inspect.stack()
        entry_frame = stack[-1]
        calling_frame = stack[2]
        show_full_config = True
        if (
            entry_frame[1].endswith("bin/djtools") and
            calling_frame[3] == "build_config"
        ):
            show_full_config = False

        for name, value in self.dict().items():
            if (
                (name in super_keys and type(self) is not BaseConfig)  # pylint: disable=unidiomatic-typecheck
                or (name not in super_keys and type(self) is BaseConfig)  # pylint: disable=unidiomatic-typecheck
            ) and not show_full_config:
                continue
            if (
                isinstance(value, list) and len(value) > 1
                and isinstance(value[0], (dict, list, set))
            ):
                ret += f"\n\t{name}=[\n\t\t"
                ret += "\n\t\t".join(str(v) for v in value)
                ret += "\n\t]"
                continue
            ret += f"\n\t{name}={str(value)}"
        ret += "\n)"

        return ret

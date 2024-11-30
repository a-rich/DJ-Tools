"""This module contains the BaseConfigFormatter. This class is a Pydantic
BaseModel that defines a __repr__ method to be used by all the config objects
used in this library."""

import logging

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class BaseConfigFormatter(BaseModel, extra="allow"):
    """Pydantic BaseModel with a __repr__ method for pretty printing."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super().__init__(*args, **kwargs)
        logger.info(repr(self))

    def __repr__(self):
        ret = f"{self.__class__.__name__}("

        for name, value in self.model_dump().items():
            if (
                isinstance(value, list)
                and len(value) > 1
                and isinstance(value[0], (dict, list, set))
            ):
                ret += f"\n\t{name}=[\n\t\t"
                ret += "\n\t\t".join(str(v) for v in value)
                ret += "\n\t]"
                continue
            ret += f"\n\t{name}={str(value)}"
        ret += "\n)"

        return ret

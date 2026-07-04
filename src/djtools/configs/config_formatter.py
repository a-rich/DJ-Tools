"""This module contains the BaseConfigFormatter. This class is a Pydantic
BaseModel that defines a __repr__ method to be used by all the config objects
used in this library."""

from typing import Any

from pydantic import BaseModel


class BaseConfigFormatter(BaseModel, extra="forbid"):
    """Pydantic BaseModel with a __repr__ method for pretty printing."""

    def _format_value(self, value: Any, indent_level: int) -> str:
        spaces = "\t" * indent_level

        if isinstance(value, BaseConfigFormatter):
            # pylint: disable=unnecessary-dunder-call
            return value.__repr__(indent=indent_level + 1).lstrip("\t")

        if (
            isinstance(value, list)
            and len(value)
            and all(isinstance(v, dict) for v in value)
        ):
            formatted_list = (
                "[\n"
                + ",\n".join(spaces + "\t" + str(v) for v in value)
                + f"\n{spaces}]"
            )
            return formatted_list

        if isinstance(value, list) and len(value):
            formatted_list = (
                "[\n"
                + ",\n".join(spaces + "\t" + repr(v) for v in value)
                + f"\n{spaces}]"
            )
            return formatted_list

        return repr(value)

    def __repr__(self, indent: int = 1) -> str:
        spaces = "\t" * (indent - 1)
        inner_spaces = "\t" * indent
        ret = f"{spaces}{self.__class__.__name__}("

        for name in self.__fields__:
            formatted_value = self._format_value(getattr(self, name), indent)
            ret += f"\n{inner_spaces}{name}={formatted_value}"

        ret += f"\n{spaces})"

        return ret

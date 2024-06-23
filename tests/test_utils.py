"""This module contains testing utilities."""

from pathlib import Path
import tempfile
from typing import IO, List, Optional, Tuple
from unittest import mock


class MockOpen:
    """Class for mocking the builtin open function."""

    builtin_open = open  # pylint: disable=used-before-assignment

    def __init__(
        self,
        files: List[str],
        user_a: Optional[Tuple[str]] = None,
        user_b: Optional[Tuple[str]] = None,
        content: Optional[str] = "",
        write_only: Optional[bool] = False,
    ):
        self._user_a = user_a
        self._user_b = user_b
        self._files = files
        self._content = content
        self._write_only = write_only

    def open(self, *args, **kwargs) -> IO:
        """Function to replace the builtin open function.

        Returns:
            File handler.
        """
        file_name = Path(args[0]).name
        if file_name in self._files:
            if "w" in kwargs.get("mode"):
                return tempfile.TemporaryFile(mode=kwargs["mode"])
            if not self._write_only:
                return self._file_strategy(file_name, *args, **kwargs)
        return self.builtin_open(*args, **kwargs)

    def _file_strategy(self, *args, **kwargs):
        """Apply logic for file contents based on file name.

        Returns:
            Mock file handler object.
        """
        data = "{}"
        if self._content:
            data = self._content

        return mock.mock_open(read_data=data)(*args, **kwargs)


def mock_exists(files, path):
    """Function for mocking the existence of pathlib.Path object."""
    ret = True
    for file_name, exists in files:
        if file_name == path.name:
            ret = exists
            break

    return ret

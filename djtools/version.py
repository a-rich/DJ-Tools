"""This module is the single source for this package's version."""
import importlib.metadata
import re


__version__ = importlib.metadata.version(__package__)

# For some reason, importlib doesn't include dashes which are necessary for
# semver.Version.parse.
major_minor_patch_regex = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")
match = re.match(major_minor_patch_regex, __version__).group()
suffix = __version__.split(match)[-1]
if suffix:
    __version__ = f"{match}-{suffix}"

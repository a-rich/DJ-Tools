"""This module is the single source for this package's version."""

import importlib.metadata
import re


def get_version() -> str:
    """Get package version.

    If this is a pre-release, reformat to be compatible with semver.

    Returns:
        Version string.
    """
    version = importlib.metadata.version(__package__)

    # For some reason, importlib doesn't include dashes which are necessary for
    # semver.Version.parse.
    major_minor_patch_regex = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")
    match = re.match(major_minor_patch_regex, version).group()
    if match:
        suffix = version.split(match)[-1]
        if suffix and not suffix.startswith("-"):
            version = f"{match}-{suffix}"

    return version

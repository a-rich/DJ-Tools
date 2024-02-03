"""Testing the version module."""

from unittest import mock

import semver
import pytest

from djtools.version import get_version


@pytest.mark.parametrize(
    "version, expected",
    [
        ("3.0.0", "3.0.0"),
        ("3.0.0rc1", "3.0.0-rc1"),
        ("3.0.0-rc.1", "3.0.0-rc.1"),
        ("3.0.0b1", "3.0.0-b1"),
        ("3.0.0-b.1", "3.0.0-b.1"),
    ],
)
@mock.patch("djtools.version.importlib.metadata.version")
def test_fix_version_string(mock_version, version, expected):
    """Test the version module's get_version function."""
    mock_version.return_value = version
    output_version = get_version()
    assert output_version == expected
    try:
        _ = semver.Version.parse(output_version)
    except ValueError:
        pytest.fail("get_version should return a parsable string")

"""Testing the main entrypoint for the djtools library."""

from unittest import mock

from djtools import main
from .test_utils import MockOpen


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["config.yaml"],
        write_only=True,
    ).open,
)
@mock.patch("djtools.upload_log", mock.Mock())
@mock.patch("djtools.UTILS_OPERATIONS")
@mock.patch("argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_utils_operations, namespace):
    """Test for the main function."""
    mock_ops = {
        "CHECK_TRACKS": lambda x, beatcloud_tracks=[]: None,
        "URL_DOWNLOAD": lambda x: None,
    }
    mock_utils_operations.items.side_effect = mock_ops.items
    namespace.check_tracks = True
    namespace.url_download = "some-url"
    mock_parse_args.return_value = namespace
    main()

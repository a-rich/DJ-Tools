"""Testing the main entrypoint for the djtools library."""
from argparse import Namespace
from unittest import mock

from djtools import main


@mock.patch("djtools.upload_log", mock.Mock())
@mock.patch("djtools.UTILS_OPERATIONS")
@mock.patch("argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_utils_operations):
    """Test for the main function."""
    mock_ops = {
        "CHECK_TRACKS": lambda x, beatcloud_tracks=[]: None,
        "URL_DOWNLOAD": lambda x: None,
    }
    mock_utils_operations.items.side_effect = mock_ops.items
    mock_parse_args.return_value = Namespace(
        link_configs="",
        log_level="INFO",
        check_tracks=True,
        url_download="some-url",
    )
    main()

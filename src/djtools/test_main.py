from argparse import Namespace
from unittest import mock

from djtools.main import main
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"], write_only=True).open
)
@mock.patch("djtools.main.upload_log")
@mock.patch("djtools.main.UTILS_OPERATIONS")
@mock.patch("argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_utils_operations, mock_upload_log):
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

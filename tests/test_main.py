"""Testing the main entrypoint for the djtools library."""

from unittest import mock

from djtools import main


@mock.patch("djtools.upload_log", mock.Mock())
@mock.patch("djtools.UTILS_OPERATIONS")
@mock.patch("djtools.configs.helpers._arg_parse")
def test_main(mock_parse_args, mock_utils_operations, config_file_teardown):
    """Test for the main function."""
    # pylint: disable=unused-argument
    mock_ops = {
        "check_tracks": lambda x, beatcloud_tracks=[]: None,
        "url_download": lambda x: None,
    }
    mock_utils_operations.items.side_effect = mock_ops.items
    mock_parse_args.return_value = {
        "check_tracks": True,
        "url_download": "some-url",
    }
    main()

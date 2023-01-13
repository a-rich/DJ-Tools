from argparse import Namespace
from unittest import mock

from djtools.main import main
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"], write_only=True).open
)
@mock.patch("argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_get_spotify_client, test_xml):
    mock_parse_args.return_value = Namespace(
        link_configs="",
        log_level="INFO",
        check_tracks=True,
        randomize_playlists=["Rock"],
        xml_path=test_xml,
    )
    main()

"""Testing for the tag_parser module."""
import pytest
import yaml

from djtools.rekordbox.playlist_combiner import Combiner
from djtools.rekordbox.tag_parsers import (
    GenreTagParser, MyTagParser, TagParser
)


def test_combiner(test_playlist_config, xml, caplog):
    """Test Combiner class."""
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    bad_playlist = "Dark & [-1, 5-7, a-5]"
    selector_playlists = [
        x for x in playlist_config["Combiner"]["playlists"]
        if "[" in x or "{" in x
    ]
    playlist_config["Combiner"]["playlists"].append(bad_playlist)
    combiner_parser = Combiner(
        parser_config=playlist_config["Combiner"],
        rekordbox_database=xml,
    )
    prescan_tag_mapping = combiner_parser.get_combiner_tracks()
    for selector in prescan_tag_mapping:
        selector = selector.strip("[").strip("]").strip("{").strip("}")
        assert any(selector in playlist for playlist in selector_playlists)
    assert caplog.records[0].message == (
        "Malformed BPM or rating filter part: -1"
    )
    assert caplog.records[1].message == (
        "Bad BPM or rating number range: 5-7"
    )
    assert caplog.records[2].message == (
        "Malformed BPM or rating filter part: a-5"
    )


def test_combiner_raises_lookuperror_for_bad_playlist(
    test_playlist_config, xml
):
    """Test Combiner class."""
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    bad_playlist = "nonexistent playlist"
    playlist_config["Combiner"]["playlists"] = [f"{{{bad_playlist}}} | Dark"]
    with pytest.raises(LookupError, match=f"{bad_playlist} not found"):
        combiner_parser = Combiner(
            parser_config=playlist_config["Combiner"],
            rekordbox_database=xml,
        )
        combiner_parser.get_playlist_mapping(xml)


def test_genretagparser(test_playlist_config, xml):
    """Test GenreTagParser class."""
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    genre = "Hip Hop"
    parser = GenreTagParser(
        parser_config=playlist_config["GenreTagParser"],
        pure_genre_playlists=[genre],
    )
    tracks = {
        track["TrackID"]: track for track in xml.find_all("TRACK")
        if track.get("Location")
    }
    playlist = xml.find_all("NODE", {"Name": genre, "Type": "1"})[0]
    for track_key in playlist.find_all("TRACK"):
        track = tracks[track_key["Key"]]
        tags = parser(track)
        assert genre in tags
        if f"Pure {genre}" in tags:
            assert all(
                genre in tag for tag in tags
            )


def test_mytagparser(test_playlist_config, xml):
    """Test MyTagParser class."""
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    mytag = "Dark"
    parser = MyTagParser(parser_config=playlist_config["MyTagParser"])
    tracks = {
        track["TrackID"]: track for track in xml.find_all("TRACK")
        if track.get("Location")
    }
    playlist = xml.find_all("NODE", {"Name": mytag, "Type": "1"})[0]
    for track_key in playlist.find_all("TRACK"):
        track = tracks[track_key["Key"]]
        tags = parser(track)
        assert mytag in tags


def test_tagparser_raises_type_error():
    """Test TagParser class."""
    with pytest.raises(
        TypeError,
        match=(
            "Can't instantiate abstract class TagParser with abstract method"
        ),
    ):
        TagParser(parser_config={})


def test_tagparser_call_raises_not_imlemented_error(test_track):
    """Test TagParser class."""
    TagParser.__abstractmethods__ = set()
    class TagParserSubclass(TagParser):
        """Dummy sub-class."""

    with pytest.raises(
        NotImplementedError,
        match=(
            "Classes inheriting from TagParser must override the __call__ "
            "method."
        ),
    ):
        TagParserSubclass(parser_config={})(test_track)

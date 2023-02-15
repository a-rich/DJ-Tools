from bs4 import BeautifulSoup
import pytest
import yaml

from djtools.rekordbox.tag_parsers import (
    Combiner, GenreTagParser, MyTagParser, TagParser
)


pytest_plugins = [
    "test_data",
]


def test_combiner(test_playlist_config, test_xml, caplog):
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    bad_playlist = "Dark & [-1, 5-7, a-5]"
    selector_playlists = [
        x for x in playlist_config["Combiner"]["playlists"]
        if "[" in x or "{" in x
    ]
    playlist_config["Combiner"]["playlists"].append(bad_playlist)
    combiner_parser = Combiner(
        parser_config=playlist_config["Combiner"],
        rekordbox_database=db,
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
    test_playlist_config, test_xml
):
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    bad_playlist = "nonexistent playlist"
    playlist_config["Combiner"]["playlists"] = [f"{{{bad_playlist}}} | Dark"]
    with pytest.raises(LookupError, match=f"{bad_playlist} not found"):
        combiner_parser = Combiner(
            parser_config=playlist_config["Combiner"],
            rekordbox_database=db,
        )
        combiner_parser.get_playlist_mapping(db)


def test_genretagparser(test_playlist_config, test_xml):
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    genre = "Techno"
    parser = GenreTagParser(
        parser_config=playlist_config["GenreTagParser"],
        pure_genre_playlists=[genre],
    )
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    tracks = {
        track["TrackID"]: track for track in db.find_all("TRACK")
        if track.get("Location")
    }
    playlist = db.find_all("NODE", {"Name": genre, "Type": "1"})[0]
    for track_key in playlist.find_all("TRACK"):
        track = tracks[track_key["Key"]]
        tags = parser(track)
        assert genre in tags
        if f"Pure {genre}" in tags:
            assert all(
                genre in tag for tag in tags
            )


def test_mytagparser(test_playlist_config, test_xml):
    with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
        playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
    mytag = "Hypnotic"
    parser = MyTagParser(parser_config=playlist_config["MyTagParser"])
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    tracks = {
        track["TrackID"]: track for track in db.find_all("TRACK")
        if track.get("Location")
    }
    playlist = db.find_all("NODE", {"Name": mytag, "Type": "1"})[0]
    for track_key in playlist.find_all("TRACK"):
        track = tracks[track_key["Key"]]
        tags = parser(track)
        assert mytag in tags


def test_tagparser_raises_type_error():
    with pytest.raises(
        TypeError,
        match=(
            "Can't instantiate abstract class TagParser with abstract method"
        ),
    ):
        TagParser()


def test_tagparser_call_raises_not_imlemented_error(test_track):
    TagParser.__abstractmethods__ = set()
    class TagParserSubclass(TagParser):
        pass

    with pytest.raises(
        NotImplementedError,
        match=(
            "Classes inheriting from TagParser must override the __call__ "
            "method."
        ),
    ):
        TagParserSubclass(parser_config={})(test_track)

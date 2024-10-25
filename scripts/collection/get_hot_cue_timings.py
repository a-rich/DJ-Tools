"""This script is used to print the time, in seconds, of hot cues in a
collection.
"""

# pylint: disable=consider-using-f-string,invalid-name,missing-class-docstring,missing-function-docstring,pointless-statement,redefined-outer-name
import json
import logging
import re

from argparse import ArgumentParser, Namespace
from pathlib import Path
from string import ascii_uppercase as uppercase_letters
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup, FeatureNotFound, Tag
except ModuleNotFoundError as exc:
    msg = (
        'The "BeautifulSoup" library is required; install with '
        "'pip install bs4'"
    )
    logger.critical(msg)
    raise RuntimeError(msg) from exc


def main() -> None:
    args = parse_args()

    setup_logging(args.log_level)

    all_tracks = get_tracks_from_collection(args.path)

    if args.tracks:
        tracks = find_tracks(all_tracks, args.tracks, args.strict_filtering)
    else:
        tracks = all_tracks

    for track in tracks:
        track.hot_cues

    if args.save:
        save_tracks(all_tracks, args.save_path)


class Track:
    def __init__(self, positions: List[Tag], name: str, artist: str) -> None:
        self._name = name
        self._artist = artist
        self._hot_cues = {
            uppercase_letters[index]: hot_cue
            for index, hot_cue in enumerate(
                sorted(positions, key=lambda x: int(x.get("Num", 0)))
            )
        }

    @classmethod
    def create(cls, tag: Tag) -> Optional["Track"]:
        name = tag.get("Name")
        artist = tag.get("Artist")

        if not name:
            logger.debug('Tag "%s" has no name' % str(tag))
            name = "NO NAME"

        if not artist:
            logger.debug('Tag "%s" has no artist' % str(tag))
            artist = "NO ARTIST"

        positions = tag.find_all("POSITION_MARK")
        if not positions:
            logger.warning('Track "%s - %s" has no hot cues!' % (name, artist))
            return None

        return cls(positions, name, artist)

    @property
    def name(self) -> str:
        return self._name

    @property
    def artist(self) -> str:
        return self._artist

    @property
    def hot_cues(self) -> None:
        logger.info('Hot cues for "%s" by "%s"' % (self.name, self.artist))
        for letter, hot_cue in self._hot_cues.items():
            logger.info("%s: %s" % (letter, hot_cue.get("Start")))

    def to_dict(self) -> str:
        return {
            "name": self.name,
            "artist": self.artist,
            "hot_cues": {
                letter: hot_cue.get("Start")
                for letter, hot_cue in self._hot_cues.items()
            },
        }


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("path", help="Path to a Rekordbox library XML export.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--tracks",
        action="append",
        type=str,
        help=(
            "One or more tracks whose hot cue timings will be displayed. "
            "These can be just the names of the tracks but, if "
            "'--strict-filtering' is enabled, they must follow this format:"
            "\n\t NAME - ARTIST."
        ),
    )
    parser.add_argument(
        "--strict-filtering",
        action="store_true",
        help=(
            "If enabled, tracks whose hot cues are displayed will only do so "
            "if both their name and artist match."
        ),
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Whether or not to save all the hot cue data as a JSON file.",
    )
    parser.add_argument(
        "--save-path",
        default="track_hot_cues.json",
        help="Default path of the JSON file created when saving.",
    )
    args = parser.parse_args()

    return args


def setup_logging(log_level: str):
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def get_tracks_from_collection(xml_path: str) -> List[Track]:
    path = Path(xml_path)
    if not path.exists():
        msg = "Could not find %s; ensure it exists!" % xml_path
        logger.critical(msg)
        raise RuntimeError(msg)

    try:
        with open(path, mode="r", encoding="utf-8") as _file:
            doc = BeautifulSoup(_file.read(), "xml")
    except FeatureNotFound as exc:
        msg = (
            'Could not open %s; please install "lxml" by running '
            "'pip install lxml'" % str(path)
        )
        logger.critical(msg)
        raise RuntimeError(msg) from exc

    tracks = list(
        filter(
            None,
            [
                Track.create(t)
                for t in doc.find_all("TRACK")
                if t.get("Location")
            ],
        )
    )

    return tracks


def find_tracks(
    all_tracks: List[Track], tracks_to_find: List[str], strict_filtering: bool
) -> List[Track]:
    set_of_tracks_to_find = set(tracks_to_find)
    matching_tracks = []

    for track in all_tracks:
        if strict_filtering:
            track_id = "%s - %s" % (track.name, track.artist)
            if track_id not in set_of_tracks_to_find:
                continue
            matching_tracks.append(track)
            continue

        if any(
            re.match(track.name, track_to_find)
            for track_to_find in set_of_tracks_to_find
        ):
            matching_tracks.append(track)

    return matching_tracks


def save_tracks(tracks: List[Track], track_path: str):
    with open(track_path, mode="w", encoding="utf-8") as _file:
        json.dump([track.to_dict() for track in tracks], _file)


if __name__ == "__main__":
    main()

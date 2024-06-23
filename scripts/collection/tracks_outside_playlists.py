"""This script is used to create a new playlist comprised of tracks which do
not appear in a given playlist (or, if using '--folder', any playlists in a
folder).
"""

from argparse import ArgumentParser
import logging
from traceback import format_exc

from bs4 import BeautifulSoup
from bs4.element import Tag


logger = logging.getLogger(__name__)


def create_playlist(_soup, tracks, new_playlist_name):
    """Creates a new playlist with name 'new_playlist_name' and inserts all the
    dangling tracks into it.

    Args:
        _soup (bs4.BeautifulSoup): parsed XML
        tracks (dict): map of TrackIDs to XML tags for dangling tracks
        new_playlist (str): new playlist name
    """
    playlists_root = _soup.find_all("NODE", {"Name": "ROOT", "Type": "0"})[0]
    new_playlist = _soup.new_tag(
        "NODE",
        Name=new_playlist_name,
        Type="1",
        KeyType="0",
        Entries=str(len(tracks)),
    )
    playlists_root.insert(0, new_playlist)
    for track_id, _ in tracks.items():
        new_playlist.append(_soup.new_tag("TRACK", Key=track_id))


def get_tracks(_soup, name, folder):
    """Finds a playlist (or folder) matching 'name' and identifies tracks which
    do not belong to the given playlist (or any of the playlists within the
    folder).

    Args:
        _soup (bs4.BeautifulSoup): parsed XML
        name (str): playlist / folder name used to exclude tracks
        folder (bool): whether or not 'name' is a folder

    Raises:
        ValueError: XML must contain playlist (or folder) matching 'name'

    Returns:
        dict: map of TrackIDs to XML tags for dangling tracks
    """
    tracks = {
        x["TrackID"]: x for x in _soup.find_all("TRACK") if x.get("Location")
    }
    try:
        node = _soup.find_all(
            "NODE", {"Name": name, "Type": "0" if folder else "1"}
        )[0]
    except IndexError:
        msg = f'Failed to find {"folder" if folder else "playlist"} {name}'
        logger.critical(msg)
        raise ValueError(msg) from IndexError

    if folder:
        playlists = node.find_all("NODE", {"Type": "1"})
    else:
        playlists = [node]

    logger.info(f"Tracks: {len(tracks)}")
    logger.info(f"Playlists: {len(playlists)}")

    for playlist in playlists:
        for track in playlist.children:
            if not (isinstance(track, Tag) and tracks.get(track["Key"])):
                continue
            del tracks[track["Key"]]

    logger.info(f"Dangling tracks: {len(tracks)}")

    return tracks


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--xml_path", required=True, type=str, help="path to Rekordbox XML"
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="playlist / folder name used to find missing tracks",
    )
    parser.add_argument(
        "--folder",
        action="store_true",
        help='set if "--name" is folder instead of playlist',
    )
    parser.add_argument(
        "--new_playlist",
        type=str,
        default="Dangling Tracks",
        help="name of playlist to create with dangling tracks",
    )
    args = parser.parse_args()

    with open(args.xml_path, encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
    try:
        create_playlist(
            soup, get_tracks(soup, args.name, args.folder), args.new_playlist
        )
    except ValueError as exc:
        logger.critical(exc)
    except Exception:
        logger.critical(f"Some error occured: {format_exc()}")

    with open(args.xml_path, mode="wb", encoding=soup.orignal_encoding) as f:
        f.write(soup.prettify("utf-8"))

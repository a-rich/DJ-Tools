"""This script is used to repair track file names that may be of an incorrect
format. The expected format for track file name is
'TRACK TITLE - ARTIST NAME.mp3'; this format is required in order for this
library to properly identify potential overlap between tracks in a Spotify
playlist(s) and tracks in the beatcloud. This format is also expected for
pre-processing tracks when populating the track title and artist ID3 tags. This
script is intended to be run as a three stage process...

(1) Running this script with just '--fuzz_ratio' will identify "bad" tracks
where the first part of the file name (split on ' - ') does not match
sufficiently with the track's ID3 tag value for track title. You should adjust
the fuzz ratio such that the output is easily readable and you can assert that
the identified tracks are indeed improperly formatted. If there are properly
formatted tracks that are incorrectly identified, you may add them to the
IGNORE_TRACKS set specified at the bottom of this script. If properly formatted
tracks are improperly identified because the ID3 tag for track title is wrong,
then those files should be re-tagged with Picard or MP3Tag or whatever tagging
software you use. They should then be re-uploaded to the beatcloud with
'upload_music' and '--aws_use_date_modified'.

(2) Running this script with '--fuzz_ratio' and '--replace' will first rename
all the "bad" tracks (with the assumption that they are of the format
'ARTIST NAME - TRACK TITLE.mp3') and then remove the old improperly formatted
file from S3 (PLEASE ONLY DO THIS IF YOU ABSOLUTELY KNOW WHAT YOU'RE DOING!).
The script will NOT proceed to upload the new file; since 'aws s3 cp' uploads
one file at a time, I figured it would be better to use the natural parallelism
that 'aws s3 sync' offers and is implicit with using this library's
'upload_music' functionality).

(2.5) After renaming the files in step 2, you can open Rekordbox and click
'File > Display All Missing Files' which will trigger Rekordbox to identify all
the files you renamed. After doing this, click "Collection" and sort by the
left-most column to aggregate all the missing files (those with a '!' symbol in
the left-most column); you can now shift-click all the missing files and create
a new playlist out of them. Name this playlist "Missing Files" or something
unique. Once this playlist is created, click
'File > Export Collection in xml format'.

(3) Running the script with '--xml_path' and '--xml_swap_playlist' will parse
the XML file (the one you created in step 2.5), find the playlist you created
with all the missing files, and fix all the track locations using the same
operation used to rename the files in step 2.

(3.5) Now that you've modified the XML file so the missing files now have the
correct Location field, you can set your import XML to be this one and import
the tracks in this missing files playlist into your collection to relocate them
while retaining the original beatgrid, hot cues, etc.
"""

# pylint: disable=import-error,no-member
from argparse import ArgumentParser
from datetime import datetime
from glob import glob
import json
import logging
import os
from urllib.parse import quote, unquote

from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
import eyed3

eyed3.log.setLevel("ERROR")


logger = logging.getLogger(__name__)
IGNORE_TRACKS = set(["Scratch Sentence 5.mp3", "Scratch Sentence 1.mp3"])


try:
    import Levenshtein  # pylint: disable=unused-import
except ImportError:
    logger.warning(
        "NOTE: Track similarity can be made faster by running "
        '`pip install "djtools[levenshtein]"`'
    )


def get_bad_tracks(_args):
    """This function globs for mp3 files on '--usb_path' (ignoring those that
    are in the IGNORE_TRACKS set), reads the track title ID3 tag, splits the
    file name on ' - ', and then computes the Levenshtein similarity between
    the two. If the similarity is below '--fuzz_ratio' these files, along with
    the file name prefix and title tag, are printed and the file paths are
    returned as a list of "bad" tracks.

    Args:
        _args (argparser.Namespace): command-line arguments

    Returns:
        list: paths to files whose ID3 title tag has a Levenshtein similarity
              below '--fuzz_ratio' from the first part of the file name
              (split on ' - ')
    """
    usb_path = os.path.join(_args.usb_path, "DJ Music", "**", "*.mp3").replace(
        os.sep, "/"
    )
    files = glob(usb_path, recursive=True)
    _bad_tracks = []
    for _file in files:
        if os.path.basename(_file) in IGNORE_TRACKS:
            continue

        file_title = os.path.basename(_file).split(" - ")[0]
        tag_title = getattr(eyed3.load(_file).tag, "title")
        fuzz_ratio = fuzz.ratio(
            file_title.lower().strip(), tag_title.lower().strip()
        )
        if (
            fuzz_ratio < _args.fuzz_ratio
            and tag_title not in file_title
            and file_title not in tag_title
        ):
            logger.info(
                f"{os.path.basename(_file)}: {file_title} vs. "
                f"{tag_title} = {fuzz_ratio}"
            )
            _bad_tracks.append(_file)

    logger.info(f"{len(_bad_tracks)} bad tracks")

    return _bad_tracks


def replace_tracks(tracks):
    """Renames "bad" tracks by reversing the prefix and suffix part of the file
    name (split on ' - '). The original "bad" files are deleted from S3.

    Args:
        tracks (list): list of "bad" tracks' file paths
    """
    s3_prefix = "s3://dj.beatcloud.com/dj/music/"
    for track in tracks:
        _dir = os.path.dirname(track)
        base_name = os.path.basename(track)
        sub_dir = os.path.basename(_dir)
        name, ext = os.path.splitext(base_name)
        artist, title = name.split(" - ")
        new_base_name = " - ".join([title, artist]) + ext
        new_name = os.path.join(dir, new_base_name).replace(os.sep, "/")
        os.rename(track, new_name)
        dest = os.path.join(s3_prefix, sub_dir, base_name).replace(os.sep, "/")
        rm_cmd = f'aws s3 rm "{dest}"'
        os.system(rm_cmd)


def fix_track_location(xml_path, playlist):
    """This function parses the XML, finds the playlist with missing files,
    finds the tracks in the missing files playlist, and then performs the
    mirror 'artist - title' -> 'title - artist' swap on the 'Location' field
    before writing the modified XML.

    Args:
        xml_path (str): path to XML containing a playlist of missing files
                        (missing because they were renamed)
        playlist (str): name of the playlist containing missing files
    """
    with open(xml_path, "r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
    lookup = {
        x["TrackID"]: x for x in soup.find_all("TRACK") if x.get("Location")
    }

    try:
        tracks = get_playlist_track_locations(soup, playlist, lookup)
    except LookupError as exc:
        logger.error(exc)
        return

    logger.info(f'{len(tracks)} tracks to repair in playlist "{playlist}"')
    for track in tracks:
        loc = track["Location"]
        dir_name = os.path.dirname(loc)
        base_name = unquote(os.path.basename(loc))
        base_name, ext = os.path.splitext(base_name)
        artist, title = base_name.split(" - ")
        new_base_name = quote(" - ".join([title, artist]) + ext)
        track["Location"] = os.path.join(dir_name, new_base_name).replace(
            os.sep, "/"
        )
        logger.info(
            f"{unquote(loc)} -> "
            + unquote(
                os.path.join(dir_name, new_base_name).replace(os.sep, "/")
            )
        )

    with open(xml_path, mode="wb", encoding=soup.orignal_encoding) as _file:
        _file.write(soup.prettify("utf-8"))


def get_playlist_track_locations(soup, _playlist, lookup):
    """Finds the playlist in the XML and then creates a list of XML tags for
    the missing tracks.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        _playlist (str): name of playlist in XML which contains missing files
        lookup (dict): map of TrackIDs to XML tags for missing tracks

    Raises:
        LookupError: XML must contain the playlist

    Returns:
        list: XML tags for tracks which appear in the provided playlist
    """
    try:
        playlist = soup.find_all("NODE", {"Name": _playlist})[0]
    except IndexError:
        raise LookupError(f"{_playlist} not found") from LookupError

    return [lookup[x["Key"]] for x in playlist.children if str(x).strip()]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--usb_path", required=True, type=str, help="path to USB"
    )
    parser.add_argument(
        "--fuzz_ratio",
        type=int,
        default=0,
        help="threshold dissimilarity between ID3 title tag and "
        "supposed title from file name",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="flag to perform file renaming and S3 delete (follow up "
        "with dj_tools upload_music)",
    )
    parser.add_argument(
        "--xml_path", type=str, help='path to "rekordbox.xml" file'
    )
    parser.add_argument(
        "--xml_swap_playlist",
        type=str,
        help="playlist name in which all tracks should have the "
        "title/artist swap performed on their location",
    )
    args = parser.parse_args()

    if args.fuzz_ratio:
        bad_tracks = get_bad_tracks(args)

        if args.replace:
            _file = f"{datetime.now().timestamp()}.json"
            with open(
                os.path.join("bad_tracks", _file).replace(os.sep, "/"),
                "w",
                encoding="utf-8",
            ) as _file:
                json.dump(bad_tracks, _file)
            replace_tracks(bad_tracks)

    if args.xml_swap_playlist:
        fix_track_location(args.xml_path, args.xml_swap_playlist)

"""This is a script for renaming files in a collection so they exist at the
desired location following this convention:
        '<usb>/DJ Music/<user>/<path-insert>/<filename>'

Users provide <usb> and <user> via the CLI. <path_insert> may also be provided
(if you want all your tracks to be in the same directory), otherwise it is
inferred from the common path between tracks of the collection. <filename> will
be the same filename for tracks unless '--infer-file-names' is provided which
enables inferring the filename using the tracks' 'title' and 'artist' ID3 tags.

The 'analyze_tracks' function is run first which will gather some statistics
regarding how many tracks don't adhere to the desired structure, how many have
a sample rate below 44.1 kHz, and how many couldn't be opened.

Running this script without setting '--actually-move-stuff' will only create an
output_rekordbox.xml which you may use to preview the modifications made to
your collection. Once you're satisfied with the analysis of your collection and
the output_rekordbox.xml, you can run with this flag set to actually relocate
your files.

NOTE: this is a move and not a copy!

Also note that you might want to preemptively delete all the tracks in your
collection (after backing everything up, of course) so that you don't have to
worry about deduplicating tracks in your collection once you import them from
the new locations.

Example usage:

Say I have all my music located under "/Users/aweeeezy/Desktop/music/" and there's
a pre-existing directory structure there that I want to preserve. I also want
to use the filenames as they are already:

    python scripts/repair/rename_files.py \
        --collection /path/to/my/rekordbox.xml \
        --usb "/Volumes/AWEEEEZY/" \
        --user aweeeezy \
        --actually-move-stuff

Instead, say we have the same scenario above except all the files in my
collection are techno so I want to collapse them into a flat directory called
"Techno":

    python scripts/repair/rename_files.py \
        --collection /path/to/my/rekordbox.xml \
        --usb "/Volumes/AWEEEEZY/" \
        --user aweeeezy \
        --actually-move-stuff \
        --path-insert "Techno"

Keep in mind that you can run this script multiple times using tailored XML
files and different arguments to '--path-insert' in order to move your library
in batches. For example, you can use the 'djtools.collection' API to filter
tracks in your collection by genre tags, substrings in their paths, or whatever
really, creating new XML files that you can run with this script to do targeted
relocations.

See the reference section for the Collection package in the docs
or ask me for more details:
https://a-rich.github.io/DJ-Tools/reference/collection/

Also checkout the developer docs on the collection API:
https://a-rich.github.io/DJ-Tools-dev-docs/tutorials/developer_docs/collections_api/

Finally, let's say we want to move everything directly under my user folder and
also rename all the files using the 'title' and 'artist' ID3 tags -- providing
an empty string for '--path-insert' will disable inferring the path suffix from
the common path of tracks in your collection:

    python scripts/repair/rename_files.py \
        --collection /path/to/my/rekordbox.xml \
        --usb "/Volumes/AWEEEEZY/" \
        --user aweeeezy \
        --actually-move-stuff \
        --path-insert "" \
        --infer-file-names
"""

# pylint: disable=import-error,redefined-outer-name,no-member
from argparse import ArgumentParser
from concurrent.futures import as_completed, ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
from typing import Dict, Optional

import eyed3
from pydub import AudioSegment
from tqdm import tqdm

from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_track import RekordboxTrack
from djtools.configs.cli_args import convert_to_paths


eyed3.log.setLevel("ERROR")


def analyze_tracks(collection: RekordboxCollection, usb: Path) -> str:
    """Determines statistics of a collection.

    Tracks are noted if:
        - their paths don't have a prefix matching the desired path
        - they don't exist at the path specified
        - they have a sample rate lower than 44.1kHz

    Args:
        collection: Collection object.
        usb: Path to a location where all tracks will be relocated.

    Returns:
        Common path across tracks in the collection.
    """

    def thread(track: RekordboxTrack, data: Dict, usb: Path) -> Path:
        """Threaded process for processing tracks.

        Args:
            track: Track object.
            data: Dictionary to store track statistics.
            usb: Path to a location where all tracks will be relocated.

        Returns:
            Path of the track.
        """
        loc = track.get_location()
        if not str(loc).startswith(str(usb)):
            data["tracks_needing_relocation"].append(str(loc))
        try:
            audio = AudioSegment.from_file(loc)
        except FileNotFoundError:
            data["tracks_unable_to_be_opened"].append(str(loc))
            return loc
        if audio.frame_rate < 44_100:
            data["tracks_with_low_sample_rate"].append(str(loc))

        return loc

    # Thread pool to process tracks in the collection.
    tracks = list(collection.get_tracks().values())
    data = {
        "tracks_needing_relocation": [],
        "tracks_with_low_sample_rate": [],
        "tracks_unable_to_be_opened": [],
    }
    locations = []
    with tqdm(total=len(tracks)) as pbar:
        with ThreadPoolExecutor(max_workers=32) as pool:
            futures = [
                pool.submit(thread, track, data, usb) for track in tracks
            ]
            for future in as_completed(futures):
                locations.append(future.result())
                pbar.update()
            locations = list(filter(None, locations))

    if not locations:
        print(
            "WARNING: none of your tracks were able to be opened...make sure "
            "whatever file system you store your music on is mounted."
        )
        data["common_path"] = ""
    else:
        data["common_path"] = os.path.commonpath(locations) + os.path.sep

    # Print statistics about tracks.
    for key, value in data.items():
        print(f"{key}: {len(value) if isinstance(value, list) else value}")

    # Write statistics to a JSON file.
    with open(
        "track_analysis_data.json",
        mode="w",
        encoding="utf-8",
    ) as _file:
        json.dump(data, _file)

    return data["common_path"]


def move_files(
    collection: RekordboxCollection,
    usb: Path,
    user: str,
    common_path: str,
    path_insert: Optional[str] = None,
    infer_file_names: bool = False,
    actually_move_stuff: bool = False,
):
    """Moves tracks in a collection to a new location.

    Given a Collection object, this function will move all the tracks to a path
    following the convention:
        '<usb>/DJ Music/<user>/<path_insert>/<filename>'

    Users provide <usb> and <user> via the CLI. <path_insert> may also be
    provided (if you want all your tracks to be in the same directory),
    otherwise it is inferred from the common path between tracks of the
    collection. <filename> will be the same filename for tracks unless
    'infer_file_names' is provided which will infer the filename using the
    tracks' 'title' and 'artist' ID3 tags.

    Args:
        collection: Collection object.
        usb: Path to a location where all tracks will be relocated.
        user: User's name to use in new track paths.
        common_path: Path common to all tracks in the collection. When
            determining new track locations, old locations will be split on
            this to infer a path suffix. Unless '--path-insert' is used, the
            inferred suffix will be inserted into the new path locations
            effectively preserving your directory structure.
        path_insert: Path to insert after "user"
        infer_file_names: If this is set, the filenames as the new track paths
            will be inferred from the 'title' and 'artist' ID3 tags.
        actually_move_stuff: If set, this will move files around.
    """

    def thread(
        track: RekordboxTrack,
        usb: Path,
        user: str,
        common_path: str,
        infer_file_names: bool,
        actually_move_stuff: bool,
        data: Dict,
    ):
        """Threaded process for processing tracks.

        Args:
            track: Track object from a Collection.
            usb: Path to a location where all tracks will be relocated.
            user: User's name to use in new track paths.
            common_path: Path common to all tracks in the collection. When
                determining new track locations, old locations will be split on
                this to infer a path suffix. Unless '--path-insert' is used,
                the inferred suffix will be inserted into the new path
                locations effectively preserving your directory structure.
            actually_move_stuff: If set, this will move files around.
            data: Dictionary to store track statistics.
        """
        loc = track.get_location()

        # Skip files that don't exist.
        if not loc.exists():
            data["tracks_unable_to_be_opened"].append(str(loc))
            if actually_move_stuff:
                return

        # Ignore track already under '<usb>/DJ Music/' as they are assumed to
        # be correct.
        if str(loc).startswith(str(usb / "DJ Music")):
            data["tracks_already_at_destination"].append(str(loc))
            return

        # Determine the part of the path between '<usb>/DJ Music/<user>/' and
        # the filename.
        if path_insert is not None:
            path_suffix = path_insert
        else:
            path_suffix = str(loc.parent).split(common_path, maxsplit=1)[-1]

        # Either use the existing filename or infer a new one using the ID3
        # tags for 'title' and 'artist'.
        if infer_file_names:
            track_id3 = eyed3.load(loc)
            title = getattr(track_id3.tag, "title")
            artist = getattr(track_id3.tag, "artist")
            if title and artist:
                filename = f"{title} - {artist}{loc.suffix}"
            else:
                data["tracks_missing_tags"].append(str(loc))
                filename = loc.name
        else:
            filename = loc.name

        # Move the track and update the location of it in the collection.
        new_loc = usb / "DJ Music" / user / path_suffix / filename
        if actually_move_stuff:
            if not new_loc.parent.exists():
                new_loc.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(loc, new_loc)
        track.set_location(new_loc)

    # Thread pool to process tracks in the collection.
    data = {
        "tracks_missing_tags": [],
        "tracks_already_at_destination": [],
        "tracks_unable_to_be_opened": [],
    }
    tracks = list(collection.get_tracks().values())
    with tqdm(total=len(tracks)) as pbar:
        with ThreadPoolExecutor(max_workers=32) as pool:
            futures = [
                pool.submit(
                    thread,
                    track,
                    usb,
                    user,
                    common_path,
                    infer_file_names,
                    actually_move_stuff,
                    data,
                )
                for track in tracks
            ]
            for future in as_completed(futures):
                future.result()
                pbar.update()

    # Serialize the updated collection to a new XML file.
    collection.serialize(path="output_rekordbox.xml")

    # Print statistics about tracks.
    for key, value in data.items():
        print(f"{key}: {len(value)}")

    # Write statistics to a JSON file.
    with open(
        "track_move_data.json",
        mode="w",
        encoding="utf-8",
    ) as _file:
        json.dump(data, _file)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--collection",
        required=True,
        type=convert_to_paths,
        help="Path to a Rekordbox XML file.",
    )
    parser.add_argument(
        "--usb",
        required=True,
        type=convert_to_paths,
        help=(
            'Path to a "DJ Music" directory where you\'d like all your music '
            "to be."
        ),
    )
    parser.add_argument(
        "--user",
        required=True,
        type=str,
        help=(
            "Your beatcloud username. This MUST be consistent with what may "
            "already exist in the beatcloud."
        ),
    )
    parser.add_argument(
        "--path-insert",
        type=str,
        help=(
            "Optional path to insert between '--user' and the basename of "
            "you files. If not provided, the part of the path between the "
            "basename and the prefix common to all tracks will be used."
        ),
    )
    parser.add_argument(
        "--infer-file-names",
        action="store_true",
        help=(
            "If set, this will change the filename to be "
            "{title} - {artist}.{ext} where 'title' and 'artist' are taken "
            "from the track's ID3 tags."
        ),
    )
    parser.add_argument(
        "--actually-move-stuff",
        action="store_true",
        help="If set, this will move files around.",
    )
    args = parser.parse_args()

    # Deserialize a Rekordbox XML file.
    collection = RekordboxCollection(args.collection)

    # This just extracts location info to see (a) what the common path is for
    # tracks in your collection and (b) what the list of tracks not located
    # under 'args.usb' is.
    #
    # Nothing destructive occurs.
    common_path = analyze_tracks(collection, args.usb)

    # This function, however, is destructive.
    #
    # It will move every file not under 'args.usb' to
    # '<args.usb>/DJ Music/<args.user>/' and modify the location in your
    # collection as well, enabling you to re-import these tracks.
    move_files(
        collection,
        args.usb,
        args.user,
        common_path,
        path_insert=args.path_insert,
        infer_file_names=args.infer_file_names,
        actually_move_stuff=args.actually_move_stuff,
    )

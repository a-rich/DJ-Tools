"""Update master track Collection with local Collection."""

# pylint: disable=duplicate-code,invalid-name
from argparse import ArgumentParser
from itertools import groupby
from pathlib import Path
from subprocess import Popen

from djtools.configs import build_config
from djtools.collection.platform_registry import PLATFORM_REGISTRY


if __name__ == "__main__":
    # Parse command-line arguments.
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "--config", required=True, help="Path to a config.yaml"
    )
    arg_parser.add_argument(
        "--collection", required=False, help="Path to local collection."
    )
    arg_parser.add_argument(
        "--master-collection",
        required=False,
        help="Path to a remote master collection.",
    )
    arg_parser.add_argument(
        "--master-collection-user",
        required=False,
        default="master",
        help="Username for remote master collection.",
    )
    arg_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite master collection tracks with matching locations.",
    )
    arg_parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Don't remove the temporary master collection after updating its tracks.",
    )
    arg_parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Don't upload the master collection after updating its tracks.",
    )
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display more stuff.",
    )
    args = arg_parser.parse_args()

    # Load config and, if provided, override path to collection.
    config_path = Path(args.config)
    config = build_config(config_path)
    if args.collection:
        collection_path = Path(args.collection)
    else:
        collection_path = config.collection.collection_path

    # Load collection and get a dict of tracks keyed by location.
    collection = PLATFORM_REGISTRY[config.collection.platform]["collection"](
        path=collection_path
    )
    tracks = {
        track.get_location().as_posix(): track
        for _, track in collection.get_tracks().items()
    }

    # Set the path to the remote master collection either from the CLI arg or
    # dynamically. The default path is:
    # <BUCKET-URL>/dj/collections/master/rekordbox_collection
    if args.master_collection:
        remote_master_collection = args.master_collection
    else:
        remote_master_collection = (
            f"{config.sync.bucket_url}/dj/collections/"
            f"{args.master_collection_user}/{config.collection.platform.value}_collection"
        )

    # Download the master collection and get a dict of its tracks too.
    master_collection_path = Path("master_collection.tmp")
    cmd = ["aws", "s3", "cp", remote_master_collection, master_collection_path]
    if collection_path.is_dir():
        cmd.append("--recursive")
    with Popen(cmd) as proc:
        proc.wait()
    master_collection = PLATFORM_REGISTRY[config.collection.platform][
        "collection"
    ](path=master_collection_path)
    master_tracks = master_collection.get_tracks()
    master_tracks = {
        track.get_location().as_posix(): track
        for _, track in master_collection.get_tracks().items()
    }

    # The old master collection tracks dict is needed for verbose info.
    old_master_tracks = dict(master_tracks)

    # If not overwriting master collection tracks, then filter the new tracks
    # by those that don't have a key in the master collection tracks dict.
    tracks = (
        tracks
        if args.overwrite
        else {k: v for k, v in tracks.items() if k not in master_tracks}
    )

    # Update master collection tracks
    master_tracks = {**master_tracks, **tracks}

    # Index only new tracks for downstream processing.
    new_tracks = [
        value for key, value in tracks.items() if key not in old_master_tracks
    ]

    # Print track counts for the different collections as well as the new
    # tracks. Print the new tracks grouped by date added.
    if args.verbose:
        print(
            f"Local tracks: {len(tracks)}\n"
            f"Master tracks: {len(old_master_tracks)}\n"
            f"New tracks: {len(new_tracks)}"
        )
        for date, tracks in groupby(
            sorted(new_tracks, key=lambda x: x.get_date_added()),
            key=lambda x: x.get_date_added(),
        ):
            tracks = list(tracks)
            print(f"{date.strftime('%Y-%m-%d')}: {len(tracks)}")
            for track in tracks:
                print(f"\t{track.get_location().name}")

    # Don't waste time serializing or uploading if there aren't any new tracks.
    if new_tracks or args.overwrite:
        master_collection.set_tracks(master_tracks)
        master_collection.serialize()
    elif not args.overwrite:
        args.skip_upload = True

    # Upload the newly updated master collection.
    if not args.skip_upload:
        cmd = [
            "aws",
            "s3",
            "cp",
            master_collection_path,
            remote_master_collection,
        ]
        if collection_path.is_dir():
            cmd.append("--recursive")
        with Popen(cmd) as proc:
            proc.wait()

    # Clean up the temporary master collection.
    if not args.skip_cleanup:
        master_collection_path.unlink()

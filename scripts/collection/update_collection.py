from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen

from djtools.configs import build_config
from djtools.collection.helpers import PLATFORM_REGISTRY


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--config", help="Path to a config.yaml")
    arg_parser.add_argument(
        "--master-collection", help="Path to a remote master collection"
    )
    arg_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite tracks with matching locations."
    )
    args = arg_parser.parse_args()

    config_path = Path(args.config)
    config = build_config(config_path)

    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=config.COLLECTION_PATH
    )
    tracks = collection.get_tracks()

    master_collection_path = Path("master_collection.tmp")
    cmd = ["aws", "s3", "cp", args.master_collection, master_collection_path]
    if config.COLLECTION_PATH.is_dir():
        cmd.append("--recursive")
    with Popen(cmd) as proc:
        proc.wait()
    master_collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=master_collection_path
    )
    master_tracks = master_collection.get_tracks()

    if args.overwrite:
        master_tracks = {**master_tracks, **tracks}
    else:
        new_tracks = {k: v for k, v in tracks.items() if k not in master_tracks}
        master_tracks.update(new_tracks)
    
    master_collection.set_tracks(master_tracks)
    master_collection.serialize()

    # cmd = ["aws", "s3", "cp", master_collection_path, args.master_collection]
    # if config.COLLECTION_PATH.is_dir():
    #     cmd.append("--recursive")
    # with Popen(cmd) as proc:
    #     proc.wait()

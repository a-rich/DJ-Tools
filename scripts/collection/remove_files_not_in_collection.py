"""Script that removes files from a USB if they're not present in a collection."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from djtools.configs import build_config
from djtools.collection.platform_registry import PLATFORM_REGISTRY


# pylint: disable=missing-function-docstring


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--usb")
    args = parser.parse_args()

    return args


def strip_base_path(path: str, spliter: str = "DJ Music") -> str:
    return path.split(spliter)[-1]


def main():
    args = parse_args()

    config_path = Path(args.config)
    usb_path = Path(args.usb)

    config = build_config(config_path)
    collection = PLATFORM_REGISTRY[config.platform]["collection"](
        path=config.collection_path
    )

    tracks = {
        strip_base_path(track.get_location().as_posix()): track
        for _, track in collection.get_tracks().items()
    }
    files = {
        strip_base_path(path.as_posix()): path
        for path in usb_path.rglob("DJ Music/**/*.*")
    }
    files_not_in_collection = {
        path: path_obj
        for path, path_obj in files.items()
        if path not in tracks
    }

    print(f"Found {len(files_not_in_collection)} files not in collection.")

    for path in files_not_in_collection.values():
        path.unlink()


if __name__ == "__main__":
    main()

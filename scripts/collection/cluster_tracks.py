"""Cluster tracks by tags."""

# pylint: disable=import-error,redefined-outer-name,duplicate-code
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans, SpectralClustering
from tqdm import tqdm

from djtools.collection.base_collection import Collection
from djtools.collection.base_playlist import Playlist
from djtools.collection.base_track import Track
from djtools.collection.platform_registry import PLATFORM_REGISTRY
from djtools.configs import build_config


EXCLUDE_TAGS = (
    "DELETE",
    "Flute",
    "Guitar",
    "Horn",
    "Piano",
    "Scratch",
    "Strings",
    "Vocal",
)
PLAYLIST_NAME = "Clusters"


def get_collection_and_playlist_class(
    config_path: Path, collection_path: Optional[Path] = None
) -> Tuple[Collection, Playlist]:
    """Get the Collection and Playlist class for the configured platform.

    Args:
        config_path: Path to config.yaml.
        collection_path: Path to collection.

    Returns:
        Tuple of Collection object and Playlist class.
    """
    config = build_config(config_path)
    collection = PLATFORM_REGISTRY[config.platform]["collection"](
        path=collection_path or config.collection_path
    )
    playlist_class = PLATFORM_REGISTRY[config.platform]["playlist"]

    return collection, playlist_class


def get_tracks(
    collection: Collection, playlists: Optional[List[str]] = None
) -> Dict[str, Track]:
    """Get tracks for the provided list of playlists.

    Args:
        collection: Collection object.
        playlists: List of playlist names.

    Returns:
        Dictionary of tracks.
    """
    if not playlists:
        tracks = collection.get_tracks()
    else:
        tracks = {}
        for playlist_name in playlists:
            for playlist in collection.get_playlists(playlist_name):
                tracks.update(playlist.get_tracks())

    return tracks


def dataprep(collection: Collection, tracks: Dict[str, Track]) -> pd.DataFrame:
    """Build a Dataframe from the track tags.

    Args:
        collection: Collection object.
        tracks: Dictionary of tracks.

    Returns:
        Dataframe of track tag data.
    """
    other_tags = sorted(
        set(collection.get_all_tags()["other"]).difference(EXCLUDE_TAGS)
    )
    dataset = []
    for track in tqdm(tracks.values(), desc="Building dataset from tracks"):
        track_id = track.get_id()
        tags = set(track.get_tags()).difference(set(track.get_genre_tags()))
        one_hot = [0] * len(other_tags)
        for index, tag in enumerate(other_tags):
            if tag not in tags:
                continue
            one_hot[index] = 1
        dataset.append((track_id, *one_hot))
    data = pd.DataFrame(dataset, columns=["id"] + other_tags, index=None)
    data.set_index("id", inplace=True)

    return data


def cluster(
    data: pd.DataFrame,
    clusters: List[int],
    playlist_class: Playlist,
    tracks: Dict[str, Track],
    cluster_algo_name: str,
) -> List[Playlist]:
    """Create playlists from tracks clustered by tag data.

    Args:
        data: Dataframe of track tag data.
        clusters: Number of clusters to build.
        playlist_class: Playlist class.
        tracks: Dictionary of tracks.
        cluster_algo_name: Clustring algorithm name.

    Returns:
        List of Playlist objects.
    """
    playlists = []
    cluster_algos = {
        "kmeans": KMeans,
        "dbscan": DBSCAN,
        "spectral": SpectralClustering,
    }

    for num_clusters in clusters:
        if cluster_algo_name in ["kmeans", "spectral"]:
            kwargs = {"n_clusters": num_clusters, "n_init": 10}
        else:
            kwargs = {"eps": num_clusters, "min_samples": 10}
        cluster_playlists = []
        cluster_algo = cluster_algos[cluster_algo_name](**kwargs).fit(data)
        if getattr(cluster_algo, "inertia_", None):
            print(
                f"{num_clusters} clusters -- inertia: {cluster_algo.inertia_}:"
            )
        else:
            print(f"{num_clusters} clusters")
        for cluster in range(num_clusters):
            indices = np.where(cluster_algo.labels_ == cluster)
            track_ids = data.iloc[indices].index.tolist()
            print(f"\t{len(track_ids)}")
            cluster_playlists.append(
                playlist_class.new_playlist(
                    name=str(cluster + 1),
                    tracks={
                        track_id: tracks[track_id] for track_id in track_ids
                    },
                )
            )
        playlists.append(
            playlist_class.new_playlist(
                name=f"{num_clusters} clusters", playlists=cluster_playlists
            )
        )

    return playlists


def save_playlists(
    collection: Collection, playlists: List[Playlist], playlist_class: Playlist
):
    """Save Playlists to Collection.

    Args:
        collection: Collection object.
        playlists: List of playlist names.
        playlist_class: Playlist class.
    """
    previous_playlists = collection.get_playlists(name=PLAYLIST_NAME)
    root = collection.get_playlists()
    for playlist in previous_playlists:
        root.remove_playlist(playlist)
    collection.add_playlist(
        playlist_class.new_playlist(name=PLAYLIST_NAME, playlists=playlists)
    )
    collection.serialize()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--cluster_algo_name",
        type=str,
        default="kmeans",
        help="Clustering algorithm to use.",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        nargs="+",
        default=[5],
        help="Number of clusters.",
    )
    parser.add_argument(
        "--collection", required=False, help="Path to collection."
    )
    parser.add_argument("--config", required=True, help="Path to config.yaml.")
    parser.add_argument(
        "--playlists", nargs="+", help="Playlist names to cluster."
    )
    args = parser.parse_args()

    collection, playlist_class = get_collection_and_playlist_class(
        Path(args.config), Path(args.collection) if args.collection else None
    )
    tracks = get_tracks(collection, args.playlists)
    dataset = dataprep(collection, tracks)
    playlists = cluster(
        dataset, args.clusters, playlist_class, tracks, args.cluster_algo_name
    )
    save_playlists(collection, playlists, playlist_class)

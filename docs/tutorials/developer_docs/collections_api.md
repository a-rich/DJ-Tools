# Using the Collections API


Interacting with your collection is easy using the API provided by implementations of `Collection`, `Track`, and `Playlist`.
For a complete description of the methods these classes provide, please see the [references](../../reference/collection/index.md).
What follows is more of a list of examples to demonstrate how quick and useful interactive collection manipulations can be. 

To load a collection, instantiate the class associated with the format of the serialized collection passed as a parameter:

```
collection = RekordboxCollection("/path/to/rekordbox.xml")
```

After you're done working with your collection, you can serialize it back into a format that you can perhaps import from or use as input to other scripts:

```
output_xml = collection.serialize("test_rekordbox.xml")
```

---

Once deserialized, you can manipulate the tracks and playlists in your collection in a variety of ways.

For example, you can filter tracks to create new playlists.

Below are a few snippets demonstrating how new playlists can be created that target tracks
with non-integer BPMs,
have BPMs that don't agree with beat grid data, 
or are WAV files.


```
collection.add_playlist(
    RekordboxPlaylist.new_playlist(
        "Non-integer BPMs",
        tracks={k: v for k, v in collection.get_tracks().items() if not v.get_bpm().is_integer()}
    )
)
```

```
collection.add_playlist(
    RekordboxPlaylist.new_playlist(
        "Goofy BPMs",
        tracks={
            k: v for k, v in collection.get_tracks().items()
            if v.get_bpm().is_integer() and
            len(v._beat_grid) > 0 and
            abs(sum([float(x["Bpm"]) for x in v._beat_grid]) / len(v._beat_grid) - v.get_bpm()) > 1
        }
    )
)
```

```
collection.add_playlist(
    RekordboxPlaylist.new_playlist(
        "wavs",
        tracks={
            k: v for k, v in collection.get_tracks().items()
            if str(v.get_location()).endswith(".wav")
        }
    )
)
```

---

Apart from adding playlists, you can also create new collections with subsets of your collection's tracks.

For example, you may have a script that operates on collections and you want to ensure that only techno tracks are operated upon. To do this you might have your collection only contain tracks where the word "techno" appears in their path:

```
collection.set_tracks(
    tracks={
        track_id: track for track_id, track in collection.get_tracks().items()
        if "techno" in str(track.get_location().parent).lower()
    }
)
```

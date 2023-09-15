# Using the Collections API


Interacting with your collection is easy using the API provided by implementations of `Collection`, `Track`, and `Playlist`.
For a complete description of the methods these classes provide, please see the [references](../../reference/collection/index.md).
What follows is more of a list of examples to demonstrate how quick and useful interactive collection manipulations can be. 

To load a collection, instantiate the class associated with format of the serialized collection passed as a parameter:

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

This snippet creates a new playlist that has all the tracks in your collection containing non-integer BPM values which is an indicator of potentially incorrect beat grids:
```
collection.add_playlist(
    RekordboxPlaylist.new_playlist(
        "Non-integer BPMs",
        tracks={k: v for k, v in collection.get_tracks().items() if not v.get_bpm().is_integer()}
    )
)
```

This snippet builds a playlist where the average BPM reported as an attribute of a track doesn't match the average of the multiple BPM values in its beat grid. This can happen if you do a bulk edit of the BPM values of your tracks without updating their beat grids.

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

This snippet will identify all the tracks in your collection that are a WAV file:

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

Apart from adding playlists, you can also overwrite the tracks in the collection to create new collections with different tracks.

For example, you may have a script that operates on input collections and you want to ensure that only techno tracks are operated upon. To do this you might have your collection only contain tracks where the word "techno" appears in their path:

```
collection.set_tracks(
    tracks={
        track_id: track for track_id, track in collection.get_tracks().items()
        if "techno" in str(track.get_location().parent).lower()
    }
)
```

from argparse import ArgumentParser
import os
import shutil
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup


def main(xml_path: str, destination: str, playlist_name: str):
	if not os.path.exists(xml_path):
		raise FileNotFoundError(f"{xml_path} does not exist")

	with open(xml_path) as _file:	
		db = BeautifulSoup(_file.read(), "xml")

	try:
		playlist = db.find_all("NODE", {"Name": playlist_name})[0]
	except IndexError:
		raise LookupError(f"{playlist_name} not found")
	
	tracks = {
		track["TrackID"]: track
		for track in db.find_all("TRACK")
		if track.get("Location")
	}

	playlist_track_keys = [
		track["Key"] for track in playlist.children
		if str(track).strip()
	]
	
	os.makedirs(destination, exist_ok=True)
	loc_prefix = "file://localhost"
	for key in playlist_track_keys:
		loc = tracks[key]["Location"]
		loc = unquote(loc)
		loc = loc.split(loc_prefix)[-1]
		shutil.copyfile(
			loc, os.path.join(destination, os.path.basename(loc))
		)		


if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("--xml", help="Path to rekordbox.xml")
	parser.add_argument("--dest", help="Folder to copy tracks to")
	parser.add_argument("--playlist", help="Playlist to copy tracks from")
	args = parser.parse_args()

	main(
		xml_path=args.xml,
		destination=args.dest,
		playlist_name=args.playlist,	
	)

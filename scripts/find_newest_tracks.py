from argparse import ArgumentParser
from datetime import datetime
from glob import glob
import os


p = ArgumentParser()
p.add_argument('--path', '-p', help='path to DJ thumbdrive')
p.add_argument('--filter', default=None, help='datetime string to filter after')
args = p.parse_args()

songs = glob(os.path.join(args.path, 'DJ Music/**/*.mp3'), recursive=True)
songs.sort(reverse=True, key=lambda x: os.path.getmtime(x))
print(f"{len(songs)} songs\nnewest song is {songs[0]} add at {datetime.fromtimestamp(os.path.getmtime(songs[0]))}")

if args.filter:
    from dateutil import parser
    date = parser.parse(args.filter)
    timestamp = date.timestamp()
    songs = list(filter(lambda x: os.path.getmtime(x) >= timestamp, songs))
    print(f"{len(songs)} songs added to since {date}")

from argparse import ArgumentParser
from datetime import datetime
from glob import glob
# import xmltodict
import json
import sys
import os



if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--path', '-p', required=True,
            help='path to root of DJ USB')
    p.add_argument('--download', '-d', nargs='+', type=str,
            choices=['music', 'xml'], default=[],
            help='download MP3s and/or rekordbox.xml')
    p.add_argument('--upload', '-u', action='store_true',
            help='upload MP3s')
    p.add_argument('--delete', action='store_true',
            help='adds --delete flag to "aws s3 sync" command (only for me)')
    args = p.parse_args()

    os.environ['AWS_PROFILE'] = 'DJ'

    if not args.download and not args.upload:
        sys.exit("WARNING: run with either/both '--download' or/and '--upload' options")

    for task in args.download:
        if task == 'music':
            print(f"Indexing local track collection for comparison...")
            old = set(glob(f"{os.path.join(args.path, 'DJ Music', '**', '*.*')}", recursive=True))

            print(f"Syncing remote track collection...")
            os.makedirs(os.path.join(args.path, 'DJ Music'), exist_ok=True)
            cmd = f"aws s3 sync s3://dj.beatcloud.com/dj/music/ '{os.path.join(args.path, 'DJ Music')}'"
            os.system(cmd)

            print(f"Comparing new tracks with indexed collection...")
            new = set(glob(f"{os.path.join(args.path, 'DJ Music', '**', '*.*')}", recursive=True))
            difference = sorted(list(new.difference(old)), key=lambda x: os.path.getmtime(x))

            print(f"Added {len(difference)} new tracks:")
            with open(f"new_music_{datetime.now().strftime('%Y-%M-%dT%H:%m:%S')}.txt", 'w') as f:
                for x in difference:
                    print(f"\t{x}")
                    f.write(f"{x}\n")
        elif task == 'xml':
            print(f"Syncing remote rekordbox.xml...")
            os.makedirs(os.path.join(args.path, 'PIONEER'), exist_ok=True)
            cmd = f"aws s3 cp s3://dj.beatcloud.com/dj/xml/rekordbox.xml '{os.path.join(args.path, 'PIONEER', 'rekordbox.xml')}'"
            os.system(cmd)

            if os.name == 'posix':
                print(f"Rewritting rekordbox.xml track locations for {args.path}...")
                """ # TODO: write XML with same whitespace formatting so Rekordbox can read it
                data = xmltodict.parse(open(os.path.join(args.path, 'PIONEER', 'rekordbox.xml'), 'r').read())
                for track in data['DJ_PLAYLISTS']['COLLECTION']['TRACK'][-1::-1]:
                    track['@Location'] = track['@Location'].replace('/Volumes/DJ/', os.path.join(args.path if os.name == 'posix' else os.path.splitdrive(args.path)[0], ''))
                json.dump(data, open(os.path.join(args.path, 'PIONEER', 'rekordbox.xml'), 'w'))
                """
                lines = open(os.path.join(args.path, 'PIONEER', 'rekordbox.xml'), 'r').readlines()
                with open(os.path.join(args.path, 'PIONEER', 'rekordbox.xml'), 'w') as f:
                    for line in lines:
                        if 'file://localhost' in line:
                            line = line.replace('/Volumes/DJ/', os.path.join(args.path if os.name == 'posix' else os.path.splitdrive(args.path)[0], ''))
                        f.write(f"{line.strip()}\n")
            else:
                print(f"Rewritting rekordbox.xml track locations for your system ({os.name}) is not yet supported")
                # example rekordbox.xml location formatted on Windows 10
                # Location="file://localhost/D:/DJ%20Music/Bass/Architek%20%26%20Visceral%20-%20Broken.mp3"

                # example rekordbox.xml location formatted on Mac
                # Location="file://localhost/Volumes/DJ_BACKUP/DJ%20Music/Bass/Architek%20%26%20Visceral%20-%20Broken.mp3"

    if args.upload:
        hidden = set(glob(f"{os.path.join(args.path, 'DJ Music', '**', '.*.*')}", recursive=True))
        if hidden:
            print(f"Removed {len(hidden)} hidden files...")
            for x in hidden:
                print(f"\t{x}")
                os.remove(x)
            print()

        print(f"Syncing local track collection...")
        cmd = f"aws s3 sync '{os.path.join(args.path, 'DJ Music')}' s3://dj.beatcloud.com/dj/music/"
        if os.environ.get('USER') == 'aweeeezy' and args.delete:
            cmd += ' --delete'
        os.system(cmd)

        if os.environ.get('USER') == 'aweeeezy':
            print(f"Syncing local rekordbox.xml...")
            cmd = f"aws s3 cp '{os.path.join(args.path, 'PIONEER', 'rekordbox.xml')}' s3://dj.beatcloud.com/dj/xml/rekordbox.xml"
            os.system(cmd)

    print(f"Done!")

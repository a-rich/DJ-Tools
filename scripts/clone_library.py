from argparse import ArgumentParser
from datetime import datetime
from glob import glob
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
    args = p.parse_args()

    os.environ['AWS_PROFILE'] = 'DJ'

    for task in args.download:
        if task == 'music':
            print(f"Indexing local track collection for comparison...")
            old = set(glob(f"{os.path.join(args.path, 'DJ Music/**/*.*')}", recursive=True))

            print(f"Syncing remote track collection...")
            os.makedirs(os.path.join(args.path, 'DJ Music'), exist_ok=True)
            cmd = f"aws s3 sync s3://dj.alexrichards.com/dj/music/ '{os.path.join(args.path, 'DJ Music')}'"
            os.system(cmd)

            print(f"Comparing new tracks with indexed collection...")
            new = set(glob(f"{os.path.join(args.path, 'DJ Music/**/*.*')}", recursive=True))
            difference = sorted(list(new.difference(old)), key=lambda x: os.path.getmtime(x))

            print(f"Added {len(difference)} new tracks:")
            with open(f"new_music_{datetime.now().strftime('%Y-%M-%dT%H:%m:%S')}.txt", 'w') as f:
                for x in difference:
                    print(f"\t{x}")
                    f.write(f"{x}\n")
        elif task == 'xml':
            print(f"Syncing remote rekordbox.xml...")
            os.makedirs(os.path.join(args.path, 'PIONEER'), exist_ok=True)
            cmd = f"aws s3 cp s3://dj.alexrichards.com/dj/xml/rekordbox.xml '{os.path.join(args.path, 'PIONEER', 'rekordbox.xml')}'"
            os.system(cmd)

    if args.upload:
        print(f"Syncing local track collection...")
        cmd = f"aws s3 sync '{os.path.join(args.path, 'DJ Music')}' s3://dj.alexrichards.com/dj/music/"
        os.system(cmd)

    print(f"Done!")
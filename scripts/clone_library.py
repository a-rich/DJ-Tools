from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from glob import glob
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
            glob_path = Path('/'.join([args.path, 'DJ Music']))
            old = set([str(p) for p in glob_path.rglob('**/*.*')])
            print(f"Found {len(old)} files")

            print(f"Syncing remote track collection...")
            os.makedirs(os.path.join(args.path, 'DJ Music'), exist_ok=True)
            cmd = f"aws s3 sync s3://dj.beatcloud.com/dj/music/ \"{os.path.join(args.path, 'DJ Music')}\""
            os.system(cmd)

            new = set([str(p) for p in glob_path.rglob('**/*.*')])
            difference = sorted(list(new.difference(old)), key=lambda x: os.path.getmtime(x))
            if difference:
                print(f"Found {len(difference)} new files")
                with open(f"new_music_{datetime.now().strftime('%Y-%M-%dT%H.%m.%S')}.txt", 'w', encoding='utf-8') as f:
                    for x in difference:
                        print(f"\t{x}")
                        f.write(f"{x}\n")
        elif task == 'xml':
            def rewrite_xml(file_):
                print(f"Syncing remote rekordbox.xml...")
                os.system(f"aws s3 cp s3://dj.beatcloud.com/dj/xml/rekordbox.xml {file_}")

                lines = open(file_, 'r', encoding='utf-8').readlines()
                with open(file_, 'w', encoding='utf-8') as f:
                    for l in lines:
                        if 'file://localhost' in l:
                            l = l.replace('/Volumes/DJ/', os.path.join(args.path
                                    if os.name == 'posix' else '/' + os.path.splitdrive(args.path)[0] + '/', ''))
                        f.write(f"{l.strip()}\n")

            if os.name == 'nt':
                pwd = os.getcwd()
                os.chdir(args.path)
                os.makedirs('PIONEER', exist_ok=True)
                os.chdir(os.path.join(args.path, 'PIONEER'))
                rewrite_xml('rekordbox.xml')
                os.chdir(pwd)
            else:
                os.makedirs(os.path.join(args.path, 'PIONEER'), exist_ok=True)
                rewrite_xml(os.path.join(args.path, 'PIONEER', 'rekordbox.xml'))

    if args.upload:
        glob_path = Path('/'.join([args.path, 'DJ Music']))
        hidden = set([str(p) for p in glob_path.rglob('**/.*.*')])
        if hidden:
            print(f"Removed {len(hidden)} hidden files...")
            for x in hidden:
                print(f"\t{x}")
                os.remove(x)
            print()

        print(f"Syncing local track collection...")
        cmd = f"aws s3 sync \"{os.path.join(args.path, 'DJ Music')}\" s3://dj.beatcloud.com/dj/music/"
        if os.environ.get('USER') == 'aweeeezy' and args.delete:
            cmd += ' --delete'
        os.system(cmd)

        if os.environ.get('USER') == 'aweeeezy':
            print(f"Syncing local rekordbox.xml...")
            cmd = f"aws s3 cp '{os.path.join(args.path, 'PIONEER', 'rekordbox.xml')}' s3://dj.beatcloud.com/dj/xml/rekordbox.xml"
            os.system(cmd)

    print(f"Done!")

from argparse import ArgumentParser
from datetime import datetime
from glob import glob
from itertools import groupby
import os
from pathlib import Path
import requests
from subprocess import Popen, PIPE, CalledProcessError
import sys
import traceback


def parse_include_exclude(_cmd):
    if args.include:
        _cmd.extend(['--exclude', '*'])
        for x in args.include:
            _cmd.extend(['--include', f'{x}/*'])
    if args.exclude:
        _cmd.extend(['--include', '*'])
        for x in args.exclude:
            _cmd.extend(['--exclude', f'{x}/*'])
    if not args.use_date_modified:
        _cmd.append('--size-only')

    return _cmd


def run_sync(_cmd):
    tracks = []
    try:
        p = Popen(_cmd, stdout=PIPE, universal_newlines=True)

        while True:
            line = p.stdout.readline()
            if line == '' and p.poll() is not None:
                break
            if 'upload: ' in line:
                print(line.strip(), flush=True)
                tracks.append(line.strip().split(' to s3://dj.beatcloud.com/dj/music/')[-1])
            else:
                print(f'{line.strip()}                                                          ',
                        end='\r', flush=True)

        p.stdout.close()
        return_code = p.wait()
        if return_code:
            raise CalledProcessError(return_code, _cmd)
    except AttributeError:
        print(f"No new track")
    except Exception as e:
        print(f"Failure while syncing: {e}")

    new_music = ''
    if tracks:
        print(f"\nSuccessfully {'down' if 's3://' in _cmd[3] else 'up'}loaded the following tracks:")
    for g, group in groupby(sorted(tracks,
            key=lambda x: '/'.join(x.split('/')[:-1])),
            key=lambda x: '/'.join(x.split('/')[:-1])):
        group = sorted(group)
        new_music += f'{g}: {len(group)}\n'
        for track in group:
            x = track.split('/')[-1]
            new_music += f'\t{x}\n'
    if new_music:
        print(new_music)

    return new_music


def webhooks(url, content=None):
    if not content:
        print("There's no content")
        return

    batch = content[:args.content_size_limit]
    remainder = content[args.content_size_limit:]
    while batch:
        index = args.content_size_limit - 1
        while True:
            try:
                if batch[index] == '\n':
                    break
            except IndexError:
                break
            index -= 1
        remainder = batch[index+1:] + remainder
        batch = batch[:index+1]

        try:
            requests.post(url, json={"content": batch})
        except Exception:
            print(traceback.format_exc())

        batch = remainder[:args.content_size_limit]
        remainder = remainder[args.content_size_limit:]



if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--path', '-p', required=True,
            help='path to root of DJ USB')
    p.add_argument('--xml_path', '-x', default='/Volumes/AWEEEEZY/',
            help='path to root of DJ USB')
    p.add_argument('--download', '-d', nargs='+', type=str,
            choices=['music', 'xml'], default=[],
            help='download MP3s and/or rekordbox.xml')
    p.add_argument('--upload', '-u', nargs='+', type=str,
            choices=['music', 'xml'], default=[],
            help='upload MP3s and/or rekordbox.xml')
    p.add_argument('--delete', action='store_true',
            help='adds --delete flag to "aws s3 sync" command (only for me)')
    p.add_argument('--include', type=str, nargs='+',
            help='--include flag for each top-level folder in "DJ Music"')
    p.add_argument('--exclude', type=str, nargs='+',
            help='--exclude flag for each top-level folder in "DJ Music"')
    p.add_argument('--use_date_modified', action='store_true',
            help='drop --size-only flag for `aws s3 sync` command; --use_date_modified will permit re-downloading/re-uploading files if their ID3 tags change')
    subparsers = p.add_subparsers(dest='use_webhooks', help="use_webhook's option subparser")
    use_webhooks_subparser = subparsers.add_parser(name='use_webhooks',
            help="use_webhooks")
    use_webhooks_subparser.add_argument('--webhook_url', type=str,
            default=os.environ.get('BEATS_R_US_DISCORD'),
            help='discord webhook URL')
    use_webhooks_subparser.add_argument('--content_size_limit', type=int,
            default=2000, help='webhook content size limit')
    args = p.parse_args()

    os.environ['AWS_PROFILE'] = 'DJ'

    if not args.download and not args.upload:
        sys.exit("WARNING: run with either/both '--download' or/and '--upload' options")

    if args.exclude and args.include:
        sys.exit("WARNING: can't run with both '--include' and '--exclude' options")

    if args.use_webhooks and not args.webhook_url:
        sys.exit("WARNING: can't run with 'use_webhooks' command unless you also set either '--webhook_url' or the environment variable 'BEATS_R_US_DISCORD'")


    for task in args.download:
        if task == 'music':
            glob_path = Path('/'.join([args.path, 'DJ Music']))
            old = set([str(p) for p in glob_path.rglob('**/*.*')])
            print(f"Found {len(old)} files")

            print(f"Syncing remote track collection...")
            os.makedirs(os.path.join(args.path, 'DJ Music'), exist_ok=True)
            cmd = ['aws', 's3', 'sync', 's3://dj.beatcloud.com/dj/music/', f"{os.path.join(args.path, 'DJ Music')}"]
            cmd = parse_include_exclude(cmd)
            _ = run_sync(cmd)

            new = set([str(p) for p in glob_path.rglob('**/*.*')])
            difference = sorted(list(new.difference(old)), key=lambda x: os.path.getmtime(x))
            if difference:
                print(f"Found {len(difference)} new files")
                with open(f"new_music_{datetime.now().strftime('%Y-%m-%dT%H.%M.%S')}.txt", 'w', encoding='utf-8') as f:
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
                            l = l.replace(args.xml_path, os.path.join(args.path
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

    for task in args.upload:
        if task == 'music' and os.environ.get('USER') == 'aweeeezy':
            glob_path = Path('/'.join([args.path, 'DJ Music']))
            hidden = set([str(p) for p in glob_path.rglob('**/.*.*')])
            if hidden:
                print(f"Removed {len(hidden)} hidden files...")
                for x in hidden:
                    print(f"\t{x}")
                    os.remove(x)
                print()

            print(f"Syncing local track collection...")
            cmd = ['aws', 's3', 'sync', f"{os.path.join(args.path, 'DJ Music')}", 's3://dj.beatcloud.com/dj/music/']
            cmd = parse_include_exclude(cmd)
            if os.environ.get('USER') == 'aweeeezy' and args.delete:
                cmd.append(' --delete')

            if args.use_webhooks:
                webhooks(args.webhook_url, run_sync(cmd))
            else:
                _ = run_sync(cmd)

        elif task == 'xml' and os.environ.get('USER') == 'aweeeezy':
            print(f"Syncing local rekordbox.xml...")
            cmd = f'''aws s3 sync '{os.path.join(args.path, 'PIONEER')}' s3://dj.beatcloud.com/dj/xml/ --exclude="*" --include="rekordbox.xml"'''
            os.system(cmd)

    print(f"Done!")

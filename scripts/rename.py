from argparse import ArgumentParser
import os
import re

parser = ArgumentParser()
parser.add_argument('--directory', '-d',
        help='directory containing songs to rename')
args = parser.parse_args()

def fix_up(f):
    stripped = ''.join(re.split(r"(\-\d{1,}\.)", f)[:1] + ['.'] + re.split(r"(\-\d{1,}\.)", f)[2:])
    print('stripped: ', stripped)
    name, ext = os.path.splitext(stripped)
    print('name, ext: ', (name, ext))
    name = ' - '.join(name.split(' - ')[-1::-1])
    print('name: ', name)
    return name + ext

names = {os.path.join(args.directory, f): os.path.join(args.directory,
        fix_up(f))
        for f in os.listdir(args.directory)}
[os.rename(old, new) for old, new in names.items()]

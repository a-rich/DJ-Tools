from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from glob import glob
from multiprocessing import cpu_count
import os
from time import time
import traceback

import eyed3
eyed3.log.setLevel("ERROR")
from tqdm import tqdm



def get_tag(x, tag='genre'):
    """Loads eyed3.core.AudioFile object and strips the split of '/' that
    objects's `tag` field.

    Args:
        x (str): Path to mp3 file.
        tag (str, optional): The `tag` attribute of the AudioFile.
                Defaults to 'genre'

    Returns:
        [type]: [description]
        set: all unique tags.
    """
    return set(map(str.strip,  str(getattr(eyed3.load(x).tag, tag)).split(args.split)))


def get_tags(tag='genre'):
    """Gets all paths to mp3 files in the list of `--included` "DJ Music"
    subdirectories. Gets the set of all `--tag` ID3 tags

    Args:
        tag (str, optional): [description]. Defaults to 'genre'.
    """
    files = set()
    for x in args.included:
        files.update(set(glob(os.path.join(args.path, 'DJ Music', x, '**/*.mp3'), recursive=True)))
    
    if args.debug:
        tags = dict()
        for x in files:
            tags_ = set(map(str.strip,  str(getattr(eyed3.load(x).tag, args.tag)).split(args.split)))
            for t in tags_:
                if t in tags:
                    tags[t] = tags[t] + [x]
                else:
                    tags[t] = [x]

        for k in sorted(tags):
            # print(f"{k} ({len([os.path.basename(x) for x in tags[k]])}): {[os.path.basename(x) for x in tags[k][:1]]}")
            print(f"{k} ({len([os.path.basename(x) for x in tags[k]])})")
    else:
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            genres = set([y for x in list(tqdm(executor.map(get_tag, files),
                    total=len(files))) for y in x])

        if args.verbose:
            seen = set()
            for x in sorted(genres):
                if x[0].lower() not in seen:
                    seen.add(x[0].lower())
                    print()
                print('\t', x)


if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--path')
    p.add_argument('--included', default=[
            "Bass", "Tech-house", "Techno",
            "Rob's Records/Arhedee Dubstep Highlight",
            "Rob's Records/Arhedee Favorites",
            "Rob's Records/ETHEREAL"])
    p.add_argument('--tag', default='genre')
    p.add_argument('--split', default='/')
    p.add_argument('--verbose', action='store_true')
    p.add_argument('--debug', action='store_true')
    args = p.parse_args()

    tags = get_tags(tag=args.tag)

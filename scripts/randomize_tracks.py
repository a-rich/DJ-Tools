import glob
import eyed3
import random
from argparse import ArgumentParser


def main(args):
    n = 0
    files = glob.glob(f"{args.folder}/**/*.mp3", recursive=True)
    random.shuffle(files)
    for f in files:
        f = eyed3.load(f)
        setattr(f.tag, args.tag, n)
        f.tag.save()
        n += 1


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--folder', '-f', default='**',
            help='Path to folder with tracks that will have their tag randomized.')
    parser.add_argument('--tag', '-t', default='track_num',
            choices=['artist', 'bpm', 'genre', 'play_count',
                    'release_date', 'title', 'track_num'],
            help='Traktor supported tag to assign a random number to.')
    args = parser.parse_args()

    main(args)

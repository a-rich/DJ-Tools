from argparse import ArgumentParser
from subprocess import Popen, PIPE
import matplotlib.pyplot as plt
import traceback
import pickle
import sys
import os


parser = ArgumentParser()
parser.add_argument('--mode', required=True,
        choices=['before', 'after', 'plot'],
        help="Use 'before 'to analyze keys the first time, use 'after' to " \
        "analyze the keys again after using Mixed in Key and compare the " \
        "results to the 'before' run, use 'plot' to ")
parser.add_argument('--path',
        help='base path to directory for song key analysis')
parser.add_argument('--exclude', default=[], nargs='+',
        help='list of geners to exclude from plot')
args = parser.parse_args()


def plot(old_keys, diff_keys):

    def bar_text(bars, values):
        print(len(bars), len(values))
        for b, bar_type in enumerate(bars):
            print(f"bar type {b} is {bar_type}")
            for idx,rect in enumerate(bar_type):
                print(f"\trect {idx} value: {values[b][idx]}")
                height = rect.get_height() / 2
                height += sum([x[idx].get_height() for x in bars[:b]])
                ax.text(rect.get_x() + rect.get_width()/2, height,
                        values[b][idx],
                        ha='center', va='bottom', rotation=0)

    fig, ax = plt.subplots()

    # ensure keys are in sorted order
    key_order = sorted(old_keys.keys())
    temp1, temp2 = {}, {}
    for k in key_order:
        if k.lower() not in [x.lower() for x in args.exclude]:
            temp1[k] = old_keys[k]
            temp2[k] = diff_keys[k]
    old_keys = temp1
    diff_keys = temp2

    ############################################################################
    ####  Percentage stacked bar chart -- key changes overall  #################
    ############################################################################

    # get numbers for overall key analysis
    total_songs = sum([len(v) for v in old_keys.values()])
    changed_songs = sum([len(v) for v in diff_keys.values()])
    same_songs = total_songs - changed_songs

    # get numbers for per genre key analysis
    data = {'Changed': [len(v) for v in diff_keys.values()],
            'Same': [len(old_keys[k]) - len(v) for k,v in diff_keys.items()]}

    # from count values to percentages
    totals = [len(v) for v in old_keys.values()]
    changed_bars = [changed_songs / total_songs * 100] + [i / j * 100 for i,j in zip(data['Changed'], totals)]
    same_bars = [same_songs / total_songs * 100] + [i / j * 100 for i,j in zip(data['Same'], totals)]
    bar_data = [changed_bars, same_bars]

    # plot
    barWidth = 0.85
    names = ['Overall'] + list(old_keys.keys())
    r = list(range(len(names)))
    bars = []

    bars.append(plt.bar(r, changed_bars, color='#f9bc86', edgecolor='white',
            width=barWidth, label="Changed"))
    bars.append(plt.bar(r, same_bars, bottom=changed_bars, color='#b5ffb9',
            edgecolor='white', width=barWidth, label="Same"))
    bar_text(bars, [[changed_songs] + data['Changed'], [same_songs] + data['Same']])

    plt.xticks(r, names, rotation=90)
    plt.xlabel("Genre")
    plt.ylabel("Number of songs")
    plt.legend(loc='upper right', bbox_to_anchor=(1.1,1.1), ncol=1)
    #plt.tight_layout(pad=2)
    plt.yticks([])
    plt.title('Changed/same keys')
    plt.show()

    ############################################################################
    ####  Bar chart -- type of key change  #####################################
    ############################################################################

    fig, ax = plt.subplots()

    # get numbers for per genre key analysis
    data = {}
    key_change_types = {
            'Major/minor': 0,
            'Minor/major': 0,
            'Root': 0,
            'Major/minor and root': 0,
            'Minor/major and root': 0}
    for k,v in diff_keys.items():
        data[k] = key_change_types.copy()
        for song, keys in v.items():
            before,after = keys

            if not before or not after:
                continue

            if before[-1] == 'A' and after[-1] == 'B' \
                    and before[:-1] != after[:-1]:
                data[k]['Major/minor and root'] += 1
            elif before[-1] == 'B' and after[-1] == 'A' \
                    and before[:-1] != after[:-1]:
                data[k]['Minor/major and root'] += 1
            elif before[-1] == 'A' and after[-1] == 'B':
                data[k]['Major/minor'] += 1
            elif before[-1] == 'B' and after[-1] == 'A':
                data[k]['Minor/major'] += 1
            else:
                data[k]['Root'] += 1

    # from count values to percentages
    totals = [sum(v.values()) for v in data.values()]
    all_totals = sum(totals)
    counts = [[data[k][k_type] for k,total in zip(data.keys(), totals)]
            for k_type in key_change_types.keys()]
    counts_all = [sum(x) for x in counts]
    bars = [[data[k][k_type] / total * 100 for k,total in zip(data.keys(), totals)]
            for k_type in key_change_types.keys()]
    bars_all = [sum([data[k][k_type] for k in data.keys()]) / all_totals * 100
            for k_type in key_change_types.keys()]
    for i,each in enumerate(bars):
        each.insert(0, bars_all[i])
    for i,each in enumerate(counts):
        each.insert(0, counts_all[i])

    # plot
    barWidth = 0.85
    names = ['Overall'] + list(data.keys())
    r = list(range(len(names)))

    colors = ['#e7fb78',
            '#fcc400',
            '#fe7f08',
            '#1b79c7',
            '#001fc0']

    _bars = []
    bottoms = [0 for _ in r]
    for b,bar in enumerate(bars):
        if b == 0:
            _bars.append(plt.bar(r, bar, color=colors[b], edgecolor='white',
                    width=barWidth, label=list(key_change_types.keys())[b]))
        else:
            _bars.append(plt.bar(r, bar, color=colors[b], edgecolor='white',
                    width=barWidth, label=list(key_change_types.keys())[b],
                    bottom=bottoms))
        for x,y in enumerate(bar):
            bottoms[x] += y
    bar_text(_bars, counts)

    plt.xticks(r, names, rotation=90)
    plt.xlabel("Genre")
    plt.ylabel("Number of songs")
    plt.legend(loc='upper right', bbox_to_anchor=(1.1,1.2), ncol=1)
    plt.yticks([])
    plt.title('Type of key change')
    plt.show()


if args.mode in ['before', 'after']:
    if not args.path:
        sys.exit(f"'path' is a required argument in '{args.mode}' mode")

    if args.mode == 'after':
        try:
            old_keys = pickle.load(open('keys.pkl', 'rb'))
        except FileNotFoundError:
            sys.exit('No existing keys.pkl file -- run in before mode first to get initial song keys')

        diff_keys = {}
        removed_songs = []
        same = different = 0

    base = args.path
    keys = {}
    cmd1 = ['ffprobe', '']
    cmd2 = ['grep', 'TKEY']
    for d in os.listdir(base):
        print(f"Getting {d} keys")
        path = base + d + '/'
        keys[d] = {}

        if args.mode == 'after':
            diff_keys[d] = {}

        songs = os.listdir(path)
        for s, song in enumerate(songs, start=1):
            if s % 50 == 0:
                print(f"\tsong {s} of {len(songs)}")
            cmd1[1] = path + song
            proc1 = Popen(cmd1, stderr=PIPE)
            proc2 = Popen(cmd2, stdin=proc1.stderr, stdout=PIPE)
            proc1.stderr.close()
            out = proc2.communicate()

            try:
                key = out[0].decode('utf-8').split(':')[-1].strip()
                keys[d][song] = key
                if args.mode == 'after':
                    if old_keys[d][song] != key:
                        diff_keys[d][song] = (old_keys[d][song], key)
                        different += 1
                    else:
                        same += 1
            except KeyError:
                if song.startswith('._'):
                    removed_songs.append(song)
                    os.remove(path + song)

    if args.mode == 'after':
        print('Removed songs:')
        for s in removed_songs:
            print('\t',s)

        print(f"same: {same}\ndifferent: {different}")
        pickle.dump(diff_keys, open('diff_keys.pkl', 'wb'))
        plot(old_keys, diff_keys)
    else:
        pickle.dump(keys, open('keys.pkl', 'wb'))
else:
    try:
        old_keys = pickle.load(open('keys.pkl', 'rb'))
    except FileNotFoundError:
        sys.exit("No existing keys.pkl file -- run in 'before' mode first to get initial song keys")

    try:
        diff_keys = pickle.load(open('diff_keys.pkl', 'rb'))
    except FileNotFoundError:
        sys.exit("No existing diff_keys.pkl file -- run in 'after' mode first to get initial song keys")

    plot(old_keys, diff_keys)


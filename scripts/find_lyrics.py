from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
from argparse import ArgumentParser
from fuzzywuzzy import fuzz
from pathlib import Path
import librosa
import mutagen
import torch
import os



p = ArgumentParser()
p.add_argument('--lyrics', nargs='+', type=str, required=True,
        help='list of lyric segments to search tracks for')
p.add_argument('--path', type=str, required=True,
        help='path to root of DJ USB')
p.add_argument('--include_dirs', nargs='+', type=str,
        help='list of parent folder names to search in --path')
p.add_argument('--fuzz_ratio', type=int, default=25,
        help='lower-bound similarity between lyric and audio')
args = p.parse_args()
args.include_dirs = set([x.lower() for x in args.include_dirs]) if args.include_dirs else []


tracks = []
# for x in Path(os.path.join(args.path, 'DJ Music')).rglob('**/*.*'):
for x in Path(args.path).rglob('**/*.*'):
    folder = os.path.basename(os.path.split(x)[0]).lower()
    if (args.include_dirs and folder in args.include_dirs) or not args.include_dirs:
        tracks.append(str(x))

print(f"Got {len(tracks)} tracks")

tokenizer = Wav2Vec2Tokenizer.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")

try:
    import Levenshtein
except:
    print(f"[WARNING]: you can get a huge speed boost fuzzy matching local files if you run `pip install python-Levenshtein`")

for x in tracks:
    try:
        sample_rate = mutagen.File(x).info.sample_rate
        audio, _ = librosa.load(x, sr=sample_rate)
        print(f"\tOpened file {x} with sample rate {sample_rate}\n{audio})")
    except Exception as e:
        print(f"\tFailed to open file {x} with sample rate {sample_rate}\n{e}")

    try:
        input_values = tokenizer(audio, return_tensors="pt").input_values
        logits = model(input_values).logits
        prediction = torch.argmax(logits, dim=-1)
        transcription = tokenizer.batch_decode(prediction)[0]
        print(f"\tTranscription:\n{transcription}")
    except Exception as e:
        print(f"\tFailed to get transcription")

    for lyric in args.lyrics:
        fuzz_ratio = fuzz.ratio(lyric.lower(), transcription.lower())
        if fuzz_ratio >= args.fuzz_ratio:
            print(f"found {lyric}")
        else:
            print(f"did not find {lyric}; {fuzz_ratio}% similar")

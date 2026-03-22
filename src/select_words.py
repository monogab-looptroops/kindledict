"""
Select Dutch words that need Hungarian translation, sorted by frequency.

Outputs one word per line to stdout. Pipe to a file or other scripts.

Usage:
    venv/bin/python src/select_words.py                  # all words
    venv/bin/python src/select_words.py --limit 1000     # top 1000
    venv/bin/python src/select_words.py --min-freq 10    # only words with freq >= 10
    venv/bin/python src/select_words.py --limit 1000 > data/batch.txt
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')
OPENSUB_FILE = os.path.join(PROJECT_ROOT, 'data', 'hu-nl-opensub.dic')


def load_frequency():
    """Load word frequencies from OpenSubtitles corpus."""
    freq = {}
    if not os.path.exists(OPENSUB_FILE):
        return freq
    with open(OPENSUB_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            try:
                count = int(parts[0])
            except ValueError:
                continue
            nl = parts[3].strip().lower()
            freq[nl] = freq.get(nl, 0) + count
    return freq


def select_words(limit=None, min_freq=0):
    """Select words without Hungarian translation, sorted by frequency."""
    freq = load_frequency()
    words = []

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        for entry in entries:
            translations = entry.get('translations', {})
            if 'hu' in translations:
                continue
            word = entry['word']
            if word.startswith('-') or not any(c.isalpha() for c in word):
                continue
            word_freq = freq.get(word.lower(), 0)
            if word_freq >= min_freq:
                words.append((word, word_freq))

    words.sort(key=lambda x: -x[1])

    if limit:
        words = words[:limit]

    return words


def main():
    limit = None
    min_freq = 0
    show_freq = '--show-freq' in sys.argv

    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        limit = int(sys.argv[idx + 1])

    if '--min-freq' in sys.argv:
        idx = sys.argv.index('--min-freq')
        min_freq = int(sys.argv[idx + 1])

    words = select_words(limit=limit, min_freq=min_freq)

    if '--stats' in sys.argv:
        with_freq = sum(1 for _, f in words if f > 0)
        print(f'Total: {len(words)}', file=sys.stderr)
        print(f'With frequency data: {with_freq}', file=sys.stderr)
        print(f'Without frequency data: {len(words) - with_freq}', file=sys.stderr)
        if words:
            print(f'Top 10:', file=sys.stderr)
            for w, f in words[:10]:
                print(f'  {w} (freq={f})', file=sys.stderr)

    for word, freq_val in words:
        if show_freq:
            print(f'{word}\t{freq_val}')
        else:
            print(word)


if __name__ == '__main__':
    main()

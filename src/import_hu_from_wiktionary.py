"""
Import Hungarian translations from the raw Dutch Wiktionary extract.

Reads data/nl-raw-extract.jsonl.gz and adds Hungarian translations
to existing dictionary entries. Quality = 5 (authoritative source).
"""

import gzip
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')
RAW_FILE = os.path.join(PROJECT_ROOT, 'data', 'nl-raw-extract.jsonl.gz')


def first_letter(word):
    for ch in word:
        if ch.isalpha():
            return ch.lower()
    return '_'


def main():
    # Step 1: Extract Dutch->Hungarian pairs from Wiktionary
    print('Extracting Hungarian translations from raw Wiktionary data...')
    hu_translations = {}  # word_lower -> list of Hungarian translations

    with gzip.open(RAW_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get('word', '').strip()
            if not word:
                continue

            trans = entry.get('translations', [])
            hu_trans = [t for t in trans if t.get('lang_code') == 'hu' and t.get('word')]

            if not hu_trans:
                continue

            key = word.lower()
            if key not in hu_translations:
                hu_translations[key] = []

            for t in hu_trans:
                hu_word = t['word'].strip()
                if hu_word and hu_word not in hu_translations[key]:
                    hu_translations[key].append(hu_word)

    print(f'  Found {len(hu_translations)} Dutch words with Hungarian translations')

    # Step 2: Merge into dictionary
    merged = 0
    already_has_hu = 0
    not_in_dict = 0

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)

        changed = False
        for entry in entries:
            key = entry['word'].lower()
            if key not in hu_translations:
                continue

            translations = entry.get('translations', {})
            if 'hu' in translations:
                already_has_hu += 1
                continue

            # Add Hungarian translation
            hu_defs = [{'text': t, 'quality': 5} for t in hu_translations[key]]
            translations['hu'] = {'definitions': hu_defs}
            entry['translations'] = translations
            merged += 1
            changed = True

        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False)
            print(f'  {filename}: merged Hungarian translations')

    # Count how many wiktionary words weren't in our dictionary
    all_dict_words = set()
    for filename in os.listdir(DICT_DIR):
        if not filename.endswith('.json'):
            continue
        with open(os.path.join(DICT_DIR, filename), 'r', encoding='utf-8') as f:
            for e in json.load(f):
                all_dict_words.add(e['word'].lower())

    not_in_dict = sum(1 for w in hu_translations if w not in all_dict_words)

    print(f'\nDone!')
    print(f'  Merged: {merged} new Hungarian translations')
    print(f'  Already had HU: {already_has_hu}')
    print(f'  Not in dictionary: {not_in_dict}')


if __name__ == '__main__':
    main()

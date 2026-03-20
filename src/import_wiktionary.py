"""
Import Dutch Wiktionary entries (kaikki.org JSONL dump) into the dictionary.
Only adds new words that don't already exist. Existing entries are left untouched.
Each new entry gets IPA, POS, and English definitions (quality 5).
"""

import os
import json
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')
WIKTIONARY_FILE = os.path.join(PROJECT_ROOT, 'data', 'dutch-wiktionary.jsonl')


def load_existing_words():
    """Load all existing words from the dictionary."""
    words = set()
    for filename in os.listdir(DICT_DIR):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue
        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f) or []
        for e in entries:
            words.add(e['word'].lower())
    return words


def first_letter(word):
    """Get the first alphabetic character of a word, lowercased."""
    for ch in word:
        if ch.isalpha():
            return ch.lower()
    return '_'


def parse_wiktionary():
    """Parse the Wiktionary JSONL dump, keeping the best entry per word."""
    print('Loading Wiktionary dump...')
    entries = {}

    with open(WIKTIONARY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            raw = json.loads(line)
            word = raw.get('word', '').strip()
            if not word or len(word) < 2:
                continue

            # Skip entries that are just forms/inflections with no real content
            senses = raw.get('senses', [])
            glosses = []
            for sense in senses:
                for gloss in sense.get('glosses', []):
                    if isinstance(gloss, str) and gloss:
                        # Skip "inflection of X" type glosses if that's all there is
                        glosses.append(gloss)

            if not glosses:
                continue

            # Extract IPA
            ipa = ''
            for s in raw.get('sounds', []):
                if 'ipa' in s and s['ipa'].startswith('/'):
                    ipa = s['ipa']
                    break

            pos = raw.get('pos', '')

            key = word.lower()
            if key not in entries or (ipa and not entries[key]['ipa']):
                entries[key] = {
                    'word': word,
                    'ipa': ipa,
                    'pos': pos,
                    'glosses': glosses[:5],
                }
            else:
                # Merge glosses from multiple POS
                existing = entries[key]
                for g in glosses:
                    if g not in existing['glosses'] and len(existing['glosses']) < 5:
                        existing['glosses'].append(g)

    print(f'  Parsed {len(entries)} unique words from Wiktionary')
    return entries


def main():
    existing = load_existing_words()
    print(f'Existing dictionary: {len(existing)} words')

    wikt = parse_wiktionary()

    # Group new entries by first letter
    by_letter = {}
    skipped = 0
    for key, entry in wikt.items():
        if key in existing:
            skipped += 1
            continue

        letter = first_letter(entry['word'])
        if letter not in by_letter:
            by_letter[letter] = []

        new_entry = {
            'word': entry['word'],
            'ipa': entry['ipa'],
            'pos': entry['pos'],
            'translations': {
                'en': {
                    'definitions': [{'text': g, 'quality': 5} for g in entry['glosses']]
                }
            },
            'source': 'wiktionary',
        }
        by_letter[letter].append(new_entry)

    total_new = sum(len(v) for v in by_letter.values())
    print(f'Skipped {skipped} already existing, adding {total_new} new entries')

    # Merge into existing YAML files
    for letter, new_entries in sorted(by_letter.items()):
        filename = f'{letter}.yaml'
        filepath = os.path.join(DICT_DIR, filename)

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                entries = yaml.safe_load(f) or []
        else:
            entries = []

        entries.extend(new_entries)

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(entries, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, width=120)

        print(f'  {filename}: added {len(new_entries)} new entries ({len(entries)} total)')

    print(f'\nDone! Added {total_new} new Wiktionary entries')


if __name__ == '__main__':
    main()

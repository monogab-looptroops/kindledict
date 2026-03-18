"""
One-time import of english/ and words/english/ into dictionary/en/.
"""

import os
import re
import yaml
from migrate import is_expression, find_key_word, first_letter, letter_for_entry

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'en')

FILES = [
    (os.path.join(PROJECT_ROOT, 'english', 'contracts'), 'english-contracts'),
    (os.path.join(PROJECT_ROOT, 'words', 'english', 'mixed'), 'english-mixed'),
]


def parse_english_file(filepath, source):
    entries = []
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        is_example = line.startswith('[') and line.endswith(']')
        if is_example:
            line = line.strip('[]')
            ws = line.split(' - ', 1)
            if len(ws) >= 2 and entries:
                hu = entries[-1]['translations'].get('hu', {})
                if 'examples' not in hu:
                    hu['examples'] = []
                hu['examples'].append({'nl': ws[0].strip(), 'tr': ws[1].strip()})
            continue

        ws = line.split(' - ', 1)
        if len(ws) < 2:
            continue

        en_text = ws[0].strip()
        hu_text = ws[1].strip()
        if not en_text or not hu_text:
            continue

        entry = {
            'word': en_text,
            'ipa': '',
            'pos': '',
            'translations': {
                'hu': {'definitions': [{'text': hu_text, 'quality': 3}]},
            },
            'source': source,
        }
        if is_expression(en_text):
            entry['expression_of'] = find_key_word(en_text)

        entries.append(entry)

    return entries


def main():
    os.makedirs(DICT_DIR, exist_ok=True)

    all_entries = []
    for filepath, source in FILES:
        if not os.path.exists(filepath):
            print(f'  Skipping {filepath} (not found)')
            continue
        entries = parse_english_file(filepath, source)
        print(f'  {source}: {len(entries)} words')
        all_entries.extend(entries)

    # Group by letter
    by_letter = {}
    for entry in all_entries:
        letter = letter_for_entry(entry)
        if letter not in by_letter:
            by_letter[letter] = []
        by_letter[letter].append(entry)

    for letter, entries in sorted(by_letter.items()):
        entries.sort(key=lambda e: e['word'].lower())
        outfile = os.path.join(DICT_DIR, f'{letter}.yaml')
        with open(outfile, 'w', encoding='utf-8') as f:
            yaml.dump(entries, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)
        print(f'  {letter}.yaml: {len(entries)} entries')

    print(f'\nTotal: {len(all_entries)} English entries')


if __name__ == '__main__':
    main()

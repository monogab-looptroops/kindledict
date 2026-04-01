"""
Apply translations from a TSV file to dictionary JSON files.

Reads tab-separated pairs (word<TAB>translation) from stdin or file.
Adds translations to entries that don't already have the target language.

Usage:
    venv/bin/python src/apply_translations.py < data/translated.tsv
    venv/bin/python src/apply_translations.py --lang hu --quality 1 < data/translated.tsv
    cat data/translated.tsv | venv/bin/python src/apply_translations.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')


def main():
    target_lang = 'hu'
    quality = 1

    if '--lang' in sys.argv:
        idx = sys.argv.index('--lang')
        target_lang = sys.argv[idx + 1]

    if '--quality' in sys.argv:
        idx = sys.argv.index('--quality')
        quality = int(sys.argv[idx + 1])

    # Read translations from stdin
    translations = {}
    for line in sys.stdin:
        line = line.strip()
        if not line or '\t' not in line:
            continue
        word, trans = line.split('\t', 1)
        translations[word] = trans

    if not translations:
        print('No translations provided on stdin.')
        return

    print(f'Loaded {len(translations)} translations (lang={target_lang}, quality={quality})')

    # Apply to dictionary
    applied = 0
    skipped = 0

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)

        changed = False
        for entry in entries:
            word = entry['word']
            if word not in translations:
                continue

            entry_trans = entry.get('translations', {})
            new_text = translations[word]

            if target_lang in entry_trans:
                # Language exists — check definitions
                existing_defs = entry_trans[target_lang].get('definitions', [])
                existing_texts = [d['text'].lower() for d in existing_defs]
                if new_text.lower() in existing_texts:
                    # Same translation — bump quality +1, max 5
                    for d in existing_defs:
                        if d['text'].lower() == new_text.lower():
                            current = d.get('quality', 1)
                            if current < 5:
                                d['quality'] = current + 1
                                changed = True
                                applied += 1
                            break
                else:
                    # Different translation — add as new definition
                    existing_defs.append({'text': new_text, 'quality': quality})
                    changed = True
                    applied += 1
            else:
                entry_trans[target_lang] = {
                    'definitions': [{'text': new_text, 'quality': quality}]
                }
                entry['translations'] = entry_trans
                changed = True
                applied += 1

        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False)

    print(f'Applied: {applied}')
    print(f'Skipped (already has {target_lang}): {skipped}')


if __name__ == '__main__':
    main()

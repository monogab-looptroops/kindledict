"""
Import Hungarian translations from OpenSubtitles parallel corpus dictionary.

Reads data/hu-nl-opensub.dic and adds/extends Hungarian translations
in existing dictionary entries. Quality = 2 (corpus-derived).

- Words without HU: adds top translations (up to 3)
- Words with HU: adds genuinely new synonyms not already present
- Skips inflected forms that are just variants of existing translations
- Prioritizes by frequency count from the subtitle corpus
"""

import json
import os
import unicodedata

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary', 'nl')
OPENSUB_FILE = os.path.join(PROJECT_ROOT, 'data', 'hu-nl-opensub.dic')

MAX_TRANSLATIONS = 3  # max new translations to add per word
MIN_COUNT = 5  # minimum occurrence count to trust a translation


def strip_accents(s):
    """Remove accents for fuzzy matching (but keep Hungarian-specific chars)."""
    return s.lower().strip()


def is_variant_of(new_word, existing_words):
    """Check if new_word is a near-duplicate of an existing translation.

    Only skips exact matches (case-insensitive). Hungarian possessive and
    other forms (apám, atyám, suliban) are genuinely useful translations,
    not just inflections to filter out.
    """
    new_lower = new_word.lower().strip()
    for existing in existing_words:
        if new_lower == existing.lower().strip():
            return True
    return False


def parse_opensub_dict():
    """Parse OpenSubtitles dictionary into NL->HU mapping."""
    nl_to_hu = {}

    with open(OPENSUB_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            try:
                count = int(parts[0])
            except ValueError:
                continue

            hu = parts[2].strip()
            nl = parts[3].strip()

            # Skip noise
            if len(nl) < 2 or len(hu) < 2:
                continue
            if count < MIN_COUNT:
                continue
            # Skip if either word is mostly non-alpha (numbers, punctuation)
            if not any(c.isalpha() for c in nl) or not any(c.isalpha() for c in hu):
                continue

            nl_lower = nl.lower()
            if nl_lower not in nl_to_hu:
                nl_to_hu[nl_lower] = []
            nl_to_hu[nl_lower].append((count, hu))

    # Sort each word's translations by frequency
    for key in nl_to_hu:
        nl_to_hu[key].sort(key=lambda x: -x[0])

    return nl_to_hu


def main():
    print('Parsing OpenSubtitles dictionary...')
    nl_to_hu = parse_opensub_dict()
    print(f'  {len(nl_to_hu)} Dutch words with Hungarian translations')

    new_hu = 0
    extended_hu = 0
    skipped = 0

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)

        changed = False
        for entry in entries:
            word_lower = entry['word'].lower()
            if word_lower not in nl_to_hu:
                continue

            candidates = nl_to_hu[word_lower]
            translations = entry.get('translations', {})
            hu_trans = translations.get('hu', {})
            existing_defs = hu_trans.get('definitions', [])
            existing_texts = [d['text'] for d in existing_defs]

            # Filter candidates: skip variants of existing translations
            new_defs = []
            for count, hu_word in candidates:
                if len(new_defs) >= MAX_TRANSLATIONS:
                    break
                if is_variant_of(hu_word, existing_texts + [d['text'] for d in new_defs]):
                    continue
                new_defs.append({'text': hu_word, 'quality': 2})

            if not new_defs:
                skipped += 1
                continue

            if existing_defs:
                # Extend existing HU translations
                existing_defs.extend(new_defs)
                hu_trans['definitions'] = existing_defs
                extended_hu += 1
            else:
                # New HU translation
                hu_trans = {'definitions': new_defs}
                new_hu += 1

            translations['hu'] = hu_trans
            entry['translations'] = translations
            changed = True

        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False)
            file_changes = sum(1 for e in entries
                             if e['word'].lower() in nl_to_hu
                             and 'hu' in e.get('translations', {}))
            print(f'  {filename}: updated')

    print(f'\nDone!')
    print(f'  New HU translations: {new_hu}')
    print(f'  Extended existing HU: {extended_hu}')
    print(f'  Skipped (no new synonyms): {skipped}')


if __name__ == '__main__':
    main()

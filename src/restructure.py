"""
Restructure dictionary from single-language to multilingual format
and enrich with Wiktionary data (English definitions, IPA, POS).

Old format:
  - word: fiets
    ipa: ''
    pos: ''
    meanings:
    - definition: bicikli
    source: mix

New format:
  - word: fiets
    ipa: /fits/
    pos: noun
    translations:
      hu:
        definitions:
        - text: bicikli
          quality: 3
        examples:
        - nl: ik ga met de fiets
          tr: biciklivel megyek
      en:
        definitions:
        - text: bicycle
          quality: 5
      nl:
        definitions:
        - text: voertuig met twee wielen
          quality: 5
    source: mix
    expression_of: ...  (if applicable)
"""

import os
import json
import yaml
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary')
WIKTIONARY_FILE = os.path.join(PROJECT_ROOT, 'data', 'dutch-wiktionary.jsonl')

# Quality levels:
# 1 = machine translated (LibreTranslate, etc.)
# 2 = from frequency list (possibly misaligned)
# 3 = human translated (from user's word files)
# 4 = verified by user
# 5 = from authoritative source (Wiktionary, etc.)

TRUSTED_SOURCES = {'wiktionary-frequency'}
USER_SOURCES_QUALITY = 3
FREQUENCY_QUALITY = 2
WIKTIONARY_QUALITY = 5


def load_wiktionary_index():
    """Load Wiktionary dump into a lookup dict keyed by lowercase word."""
    print('Loading Wiktionary dump...')
    index = {}
    with open(WIKTIONARY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get('word', '').lower()
            if not word:
                continue

            # Extract IPA (first phonemic transcription with /.../)
            ipa = ''
            for s in entry.get('sounds', []):
                if 'ipa' in s and s['ipa'].startswith('/'):
                    ipa = s['ipa']
                    break

            # Extract POS
            pos = entry.get('pos', '')

            # Extract English glosses
            glosses = []
            for sense in entry.get('senses', []):
                for gloss in sense.get('glosses', []):
                    if isinstance(gloss, str) and gloss:
                        glosses.append(gloss)

            # Keep the best entry per word (prefer entries with IPA)
            if word not in index or (ipa and not index[word].get('ipa')):
                index[word] = {
                    'ipa': ipa,
                    'pos': pos,
                    'en_glosses': glosses,
                }
            else:
                # Merge glosses from multiple POS entries
                existing = index[word]
                for g in glosses:
                    if g not in existing['en_glosses']:
                        existing['en_glosses'].append(g)

    print(f'  Loaded {len(index)} unique words')
    return index


def convert_entry(entry, wikt_index):
    """Convert an old-format entry to the new multilingual format."""
    word = entry['word']
    word_lower = word.lower()

    # Determine quality based on source
    source = entry.get('source', '')
    if source in TRUSTED_SOURCES:
        hu_quality = FREQUENCY_QUALITY
    else:
        hu_quality = USER_SOURCES_QUALITY

    # Build Hungarian translation from old meanings
    hu_defs = []
    hu_examples = []
    for meaning in entry.get('meanings', []):
        defn = meaning.get('definition', '')
        if defn:
            hu_def = {'text': defn, 'quality': hu_quality}
            # Preserve English hint if present
            if meaning.get('english'):
                hu_def['english_hint'] = meaning['english']
            hu_defs.append(hu_def)
        for ex in meaning.get('examples', []):
            hu_examples.append({
                'nl': ex.get('nl', ''),
                'tr': ex.get('hu', ''),
            })

    # Build translations dict
    translations = {}
    if hu_defs:
        hu_trans = {'definitions': hu_defs}
        if hu_examples:
            hu_trans['examples'] = hu_examples
        translations['hu'] = hu_trans

    # Look up Wiktionary data
    wikt = wikt_index.get(word_lower)

    # Get IPA and POS from Wiktionary (or keep existing if already set)
    ipa = entry.get('ipa', '') or ''
    pos = entry.get('pos', '') or ''
    if wikt:
        if not ipa and wikt['ipa']:
            ipa = wikt['ipa']
        if not pos and wikt['pos']:
            pos = wikt['pos']

        # Add English translation from Wiktionary
        if wikt['en_glosses']:
            en_defs = []
            for gloss in wikt['en_glosses'][:5]:  # limit to 5 glosses
                en_defs.append({'text': gloss, 'quality': WIKTIONARY_QUALITY})
            translations['en'] = {'definitions': en_defs}

    # Build new entry
    new_entry = {
        'word': word,
        'ipa': ipa,
        'pos': pos,
        'translations': translations,
        'source': source,
    }

    if 'expression_of' in entry:
        new_entry['expression_of'] = entry['expression_of']

    return new_entry


def main():
    wikt_index = load_wiktionary_index()

    # Process each letter file
    total = 0
    enriched_ipa = 0
    enriched_pos = 0
    enriched_en = 0

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue

        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f) or []

        new_entries = []
        for entry in entries:
            # Skip if already in new format
            if 'translations' in entry:
                new_entries.append(entry)
                total += 1
                continue

            new_entry = convert_entry(entry, wikt_index)
            new_entries.append(new_entry)
            total += 1

            if new_entry['ipa']:
                enriched_ipa += 1
            if new_entry['pos']:
                enriched_pos += 1
            if 'en' in new_entry['translations']:
                enriched_en += 1

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(
                new_entries, f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
        print(f'  {filename}: {len(new_entries)} entries')

    print(f'\nTotal: {total} entries')
    print(f'  With IPA: {enriched_ipa} ({enriched_ipa*100//total}%)')
    print(f'  With POS: {enriched_pos} ({enriched_pos*100//total}%)')
    print(f'  With English: {enriched_en} ({enriched_en*100//total}%)')


if __name__ == '__main__':
    main()

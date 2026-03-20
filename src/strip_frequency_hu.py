"""
One-time cleanup: strip broken Hungarian translations from wiktionary-frequency entries.
Keeps the Dutch words, IPA, POS, and English translations (which are correct from Wiktionary).
Removes entries that have no translations left after stripping.
"""

import os
import yaml

DICT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dictionary', 'nl')


def main():
    total_stripped = 0
    total_removed = 0

    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue

        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f) or []

        cleaned = []
        file_stripped = 0
        file_removed = 0

        for e in entries:
            if e.get('source') != 'wiktionary-frequency':
                cleaned.append(e)
                continue

            # Remove HU translations
            translations = e.get('translations', {})
            translations.pop('hu', None)

            if translations:
                e['translations'] = translations
                cleaned.append(e)
                file_stripped += 1
            else:
                # No translations left, remove the entry entirely
                file_removed += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(cleaned, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, width=120)

        if file_stripped or file_removed:
            print(f'  {filename}: stripped HU from {file_stripped}, removed {file_removed} empty entries ({len(cleaned)} remaining)')

        total_stripped += file_stripped
        total_removed += file_removed

    print(f'\nTotal: stripped HU from {total_stripped} entries, removed {total_removed} entries with no translations left')


if __name__ == '__main__':
    main()

"""
Generate Kindle dictionary HTML from the multilingual YAML dictionary files.

Reads dictionary/*.yaml and produces content_gen.html using the Jinja2 template.

Usage:
    cd src && ../venv/bin/python generate.py
"""

import os
import yaml
import jinja2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary')

# Language display order and quality symbols for Kindle
QUALITY_SYMBOLS = {1: '*', 2: '**', 3: '***', 4: '****', 5: '*****'}
LANG_LABELS = {
    'hu': 'HU',
    'en': 'EN',
    'es': 'ES',
    'nl': 'NL',
    'de': 'DE',
    'fr': 'FR',
}
# Order in which languages appear in the Kindle entry
LANG_ORDER = ['hu', 'en', 'es', 'de', 'fr', 'nl']


def load_dictionary():
    """Load all YAML dictionary files and return a flat sorted list."""
    all_entries = []
    for filename in sorted(os.listdir(DICT_DIR)):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue
        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f)
        if entries:
            all_entries.extend(entries)
    all_entries.sort(key=lambda e: e['word'].lower())
    return all_entries


def prepare_entry(entry):
    """Prepare an entry for the Jinja2 template."""
    translations = entry.get('translations', {})
    langs = []
    # Sort languages by LANG_ORDER
    for lang in LANG_ORDER:
        if lang in translations:
            trans = translations[lang]
            defs = trans.get('definitions', [])
            examples = trans.get('examples', [])
            langs.append({
                'code': lang,
                'label': LANG_LABELS.get(lang, lang.upper()),
                'definitions': defs,
                'examples': examples,
            })
    # Add any remaining languages not in LANG_ORDER
    for lang in translations:
        if lang not in LANG_ORDER:
            trans = translations[lang]
            langs.append({
                'code': lang,
                'label': LANG_LABELS.get(lang, lang.upper()),
                'definitions': trans.get('definitions', []),
                'examples': trans.get('examples', []),
            })

    return {
        'word': entry['word'],
        'ipa': entry.get('ipa', ''),
        'pos': entry.get('pos', ''),
        'langs': langs,
    }


def create_file():
    templateLoader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
    env = jinja2.Environment(loader=templateLoader)
    t = env.get_template('frame.html')

    entries = load_dictionary()
    prepared = [prepare_entry(e) for e in entries]

    outfile = os.path.join(PROJECT_ROOT, 'content_gen.html')
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(t.render(words=prepared))

    print(f'Generated {outfile} with {len(prepared)} entries')


if __name__ == '__main__':
    create_file()

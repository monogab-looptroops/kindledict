"""
Generate Kindle dictionary HTML from the multilingual YAML dictionary files.

Reads dictionary/<lang>/*.yaml and produces content_gen.html using the Jinja2 template.

Usage:
    cd src && ../venv/bin/python generate.py          # generate Dutch dictionary
    cd src && ../venv/bin/python generate.py --lang en # generate English dictionary
"""

import os
import sys
import yaml
import jinja2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LANG_LABELS = {
    'hu': 'HU', 'en': 'EN', 'es': 'ES', 'nl': 'NL', 'de': 'DE', 'fr': 'FR',
}
LANG_ORDER = ['hu', 'en', 'es', 'de', 'fr', 'nl']


def load_dictionary(lang):
    """Load all YAML dictionary files for a language and return a flat sorted list."""
    dict_dir = os.path.join(PROJECT_ROOT, 'dictionary', lang)
    all_entries = []
    for filename in sorted(os.listdir(dict_dir)):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue
        filepath = os.path.join(dict_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f)
        if entries:
            all_entries.extend(entries)
    all_entries.sort(key=lambda e: e['word'].lower())
    return all_entries


def prepare_entry(entry, source_lang):
    """Prepare an entry for the Jinja2 template."""
    translations = entry.get('translations', {})
    langs = []
    # Sort: show all languages except the source language first, source language last
    order = [l for l in LANG_ORDER if l != source_lang]
    order.append(source_lang)
    for lang in order:
        if lang in translations:
            trans = translations[lang]
            langs.append({
                'code': lang,
                'label': LANG_LABELS.get(lang, lang.upper()),
                'definitions': trans.get('definitions', []),
                'examples': trans.get('examples', []),
            })
    # Add any remaining languages
    for lang in translations:
        if lang not in order:
            langs.append({
                'code': lang,
                'label': LANG_LABELS.get(lang, lang.upper()),
                'definitions': translations[lang].get('definitions', []),
                'examples': translations[lang].get('examples', []),
            })

    return {
        'word': entry['word'],
        'ipa': entry.get('ipa', ''),
        'pos': entry.get('pos', ''),
        'langs': langs,
    }


def create_file(lang='nl'):
    templateLoader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
    env = jinja2.Environment(loader=templateLoader)
    t = env.get_template('frame.html')

    entries = load_dictionary(lang)
    prepared = [prepare_entry(e, lang) for e in entries]

    outfile = os.path.join(PROJECT_ROOT, f'content_gen_{lang}.html')
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(t.render(words=prepared))

    print(f'Generated {outfile} with {len(prepared)} entries for {lang} dictionary')


if __name__ == '__main__':
    lang = 'nl'
    if '--lang' in sys.argv:
        idx = sys.argv.index('--lang')
        lang = sys.argv[idx + 1]
    create_file(lang)

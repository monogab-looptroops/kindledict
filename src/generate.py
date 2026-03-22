"""
Generate Kindle dictionary from the multilingual JSON dictionary files.

Produces one HTML file per letter + an OPF package file for KindleGen.
Split files make KindleGen much faster and use less memory.

Usage:
    venv/bin/python src/generate.py              # generate Dutch dictionary
    venv/bin/python src/generate.py --lang en    # generate English dictionary
"""

import json
import os
import sys
import jinja2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')

LANG_LABELS = {
    'hu': 'HU', 'en': 'EN', 'es': 'ES', 'nl': 'NL', 'de': 'DE', 'fr': 'FR',
}
LANG_ORDER = ['hu', 'en', 'es', 'de', 'fr', 'nl']

LANG_NAMES = {
    'nl': 'Nederlands', 'en': 'English', 'hu': 'Magyar',
    'de': 'Deutsch', 'fr': 'Français', 'es': 'Español',
}


def load_dictionary_by_letter(lang):
    """Load JSON dictionary files grouped by letter."""
    dict_dir = os.path.join(PROJECT_ROOT, 'dictionary', lang)
    by_letter = {}
    for filename in sorted(os.listdir(dict_dir)):
        if not filename.endswith('.json'):
            continue
        letter = filename.replace('.json', '')
        filepath = os.path.join(dict_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        if entries:
            entries.sort(key=lambda e: e['word'].lower())
            by_letter[letter] = entries
    return by_letter


def prepare_entry(entry, source_lang):
    """Prepare an entry for the Jinja2 template."""
    translations = entry.get('translations', {})
    langs = []
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


def generate_opf(lang, content_files):
    """Generate the OPF package file."""
    lang_name = LANG_NAMES.get(lang, lang)
    title = f'{lang_name} Multilingual Dictionary'

    manifest_items = []
    spine_items = []

    # Add supporting files
    for fid, fname in [('cover', 'cover.html'), ('usage', 'usage.html'), ('copyright', 'copyright.html')]:
        src = os.path.join(PROJECT_ROOT, fname)
        if os.path.exists(src):
            # Copy to build dir
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(os.path.join(BUILD_DIR, fname), 'w', encoding='utf-8') as f:
                f.write(content)
            manifest_items.append(f'    <item id="{fid}" href="{fname}" media-type="application/xhtml+xml" />')
            spine_items.append(f'    <itemref idref="{fid}" />')

    # Add content files
    for i, fname in enumerate(content_files):
        fid = f'content_{i}'
        manifest_items.append(f'    <item id="{fid}" href="{fname}" media-type="application/xhtml+xml" />')
        spine_items.append(f'    <itemref idref="{fid}" />')

    opf = f'''<?xml version="1.0"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="BookId">nl-multilingual-dict-001</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator opf:role="aut">Gabor Monostori</dc:creator>
    <dc:language>{lang}</dc:language>
    <x-metadata>
      <DictionaryInLanguage>{lang}</DictionaryInLanguage>
      <DictionaryOutLanguage>{lang}</DictionaryOutLanguage>
      <DefaultLookupIndex>default</DefaultLookupIndex>
    </x-metadata>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine>
{chr(10).join(spine_items)}
  </spine>
  <guide>
    <reference type="index" title="IndexName" href="{content_files[0]}"/>
  </guide>
</package>'''

    opf_path = os.path.join(BUILD_DIR, 'dict.opf')
    with open(opf_path, 'w', encoding='utf-8') as f:
        f.write(opf)
    return opf_path


def create_files(lang='nl'):
    os.makedirs(BUILD_DIR, exist_ok=True)

    templateLoader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
    env = jinja2.Environment(loader=templateLoader)
    t = env.get_template('frame.html')

    by_letter = load_dictionary_by_letter(lang)
    content_files = []
    total = 0

    for letter in sorted(by_letter.keys()):
        entries = by_letter[letter]
        prepared = [prepare_entry(e, lang) for e in entries]
        total += len(prepared)

        filename = f'content_{letter}.html'
        filepath = os.path.join(BUILD_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(t.render(words=prepared))

        content_files.append(filename)
        print(f'  {filename}: {len(prepared)} entries')

    opf_path = generate_opf(lang, content_files)
    print(f'\nGenerated {len(content_files)} HTML files + dict.opf in build/')
    print(f'Total: {total} entries')
    print(f'\nTo build .mobi:')
    print(f'  "/Applications/Kindle Previewer 3.app/Contents/lib/fc/bin/kindlegen" {opf_path} -o dict.mobi')


if __name__ == '__main__':
    lang = 'nl'
    if '--lang' in sys.argv:
        idx = sys.argv.index('--lang')
        lang = sys.argv[idx + 1]
    create_files(lang)

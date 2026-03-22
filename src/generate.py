"""
Generate dictionaries for multiple e-reader formats.

Supported formats:
    kindle  - Kindle .mobi (HTML + OPF for KindleGen)
    kobo    - Kobo dicthtml (zipped HTML)
    stardict - StarDict .ifo/.idx/.dict (PocketBook, KOReader, GoldenDict)

Usage:
    venv/bin/python src/generate.py                        # Kindle (default)
    venv/bin/python src/generate.py --format kobo
    venv/bin/python src/generate.py --format stardict
    venv/bin/python src/generate.py --format all
    venv/bin/python src/generate.py --lang en --format all
"""

import json
import os
import struct
import sys
import zipfile
import html as html_module
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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def load_all_entries(lang):
    """Load all entries as a flat sorted list."""
    by_letter = load_dictionary_by_letter(lang)
    entries = []
    for letter in sorted(by_letter.keys()):
        entries.extend(by_letter[letter])
    return entries


def prepare_entry(entry, source_lang):
    """Prepare an entry for templates."""
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


def format_definition_text(prepared):
    """Format a prepared entry as plain text for StarDict/simple formats."""
    parts = []
    if prepared['ipa']:
        parts.append(prepared['ipa'])
    if prepared['pos']:
        parts.append(f"({prepared['pos']})")
    if parts:
        header = ' '.join(parts)
    else:
        header = ''

    lines = []
    if header:
        lines.append(header)
    for lang in prepared['langs']:
        defs = ', '.join(d['text'] for d in lang['definitions'])
        if defs:
            lines.append(f"{lang['label']}: {defs}")
        for ex in lang['examples']:
            lines.append(f"  \"{ex.get('nl', '')}\" — {ex.get('tr', '')}")
    return '\n'.join(lines)


def format_definition_html(prepared):
    """Format a prepared entry as HTML for Kobo."""
    esc = html_module.escape
    parts = []
    if prepared['ipa']:
        parts.append(f'<i style="color:#666">{esc(prepared["ipa"])}</i>')
    if prepared['pos']:
        parts.append(f'<i style="color:#888">{esc(prepared["pos"])}</i>')
    header = ' '.join(parts)

    lines = []
    if header:
        lines.append(header)
    for lang in prepared['langs']:
        defs = ', '.join(esc(d['text']) for d in lang['definitions'])
        if defs:
            lines.append(f"<b>{esc(lang['label'])}</b>: {defs}")
        for ex in lang['examples']:
            lines.append(f'<i>"{esc(ex.get("nl", ""))}" — {esc(ex.get("tr", ""))}</i>')
    return '<br/>'.join(lines)


# ---------------------------------------------------------------------------
# Kindle format
# ---------------------------------------------------------------------------

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


def create_kindle_files(lang='nl'):
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


# ---------------------------------------------------------------------------
# Kobo format
# ---------------------------------------------------------------------------

def create_kobo_files(lang='nl'):
    """Generate a Kobo dicthtml zip file."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    entries = load_all_entries(lang)

    # Group entries by first 2 chars of word (Kobo prefix scheme)
    by_prefix = {}
    for entry in entries:
        word = entry['word']
        prefix = word[:2].lower() if len(word) >= 2 else word[0].lower() if word else '_'
        if prefix not in by_prefix:
            by_prefix[prefix] = []
        by_prefix[prefix].append(entry)

    # Build HTML files per prefix
    html_files = {}
    for prefix, prefix_entries in sorted(by_prefix.items()):
        parts = ['<html><body>']
        for entry in prefix_entries:
            prepared = prepare_entry(entry, lang)
            word = html_module.escape(entry['word'])
            word_lower = entry['word'].lower().strip()
            definition = format_definition_html(prepared)
            parts.append(f'<w><a name="{word_lower}" /><p><b>{word}</b></p>')
            parts.append(f'<var><variant name="{word_lower}"/></var>')
            parts.append(f'{definition}</w>')
        parts.append('</body></html>')
        html_files[prefix] = '\n'.join(parts)

    # Create zip
    zip_name = f'dicthtml-{lang}.zip'
    zip_path = os.path.join(BUILD_DIR, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for prefix, html_content in sorted(html_files.items()):
            zf.writestr(f'{prefix}.html', html_content.encode('utf-8'))

    total = len(entries)
    print(f'\nGenerated Kobo dictionary: {zip_name}')
    print(f'Total: {total} entries in {len(html_files)} prefix files')
    print(f'\nInstall: copy {zip_name} to <Kobo>/.kobo/dict/')


# ---------------------------------------------------------------------------
# StarDict format
# ---------------------------------------------------------------------------

def stardict_sort_key(word):
    """Sort key matching StarDict requirements: case-insensitive, then case-sensitive."""
    return (word.lower(), word)


def create_stardict_files(lang='nl'):
    """Generate StarDict .ifo/.idx/.dict files."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    entries = load_all_entries(lang)
    lang_name = LANG_NAMES.get(lang, lang)
    dict_name = f'{lang_name} Multilingual Dictionary'
    base_name = f'dict-{lang}'

    # Sort entries per StarDict spec
    entries.sort(key=lambda e: stardict_sort_key(e['word']))

    # Build .dict and .idx simultaneously
    dict_data = bytearray()
    idx_data = bytearray()
    word_count = 0

    for entry in entries:
        prepared = prepare_entry(entry, lang)
        definition = format_definition_text(prepared)
        if not definition:
            continue

        word = entry['word']
        word_bytes = word.encode('utf-8')
        def_bytes = definition.encode('utf-8')

        # .idx: word\0 + offset(4B) + size(4B)
        offset = len(dict_data)
        size = len(def_bytes)
        idx_data.extend(word_bytes)
        idx_data.append(0)  # null terminator
        idx_data.extend(struct.pack('>I', offset))
        idx_data.extend(struct.pack('>I', size))

        # .dict: raw definition bytes
        dict_data.extend(def_bytes)
        word_count += 1

    # Write .dict
    dict_path = os.path.join(BUILD_DIR, f'{base_name}.dict')
    with open(dict_path, 'wb') as f:
        f.write(dict_data)

    # Write .idx
    idx_path = os.path.join(BUILD_DIR, f'{base_name}.idx')
    with open(idx_path, 'wb') as f:
        f.write(idx_data)

    # Write .ifo
    ifo_path = os.path.join(BUILD_DIR, f'{base_name}.ifo')
    with open(ifo_path, 'w', encoding='utf-8') as f:
        f.write('StarDict\'s dict ifo file\n')
        f.write('version=2.4.2\n')
        f.write(f'bookname={dict_name}\n')
        f.write(f'wordcount={word_count}\n')
        f.write(f'idxfilesize={len(idx_data)}\n')
        f.write('sametypesequence=m\n')
        f.write('author=Gabor Monostori\n')

    print(f'\nGenerated StarDict dictionary: {base_name}.ifo/.idx/.dict')
    print(f'Total: {word_count} entries')
    print(f'\nInstall: copy all 3 files to your dictionary folder')
    print(f'  PocketBook/KOReader: applications/koreader/data/dict/')
    print(f'  GoldenDict: add folder in settings')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FORMATS = {
    'kindle': create_kindle_files,
    'kobo': create_kobo_files,
    'stardict': create_stardict_files,
}


if __name__ == '__main__':
    lang = 'nl'
    fmt = 'kindle'
    if '--lang' in sys.argv:
        idx = sys.argv.index('--lang')
        lang = sys.argv[idx + 1]
    if '--format' in sys.argv:
        idx = sys.argv.index('--format')
        fmt = sys.argv[idx + 1]

    if fmt == 'all':
        for name, func in FORMATS.items():
            print(f'=== {name.upper()} ===')
            func(lang)
            print()
    elif fmt in FORMATS:
        FORMATS[fmt](lang)
    else:
        print(f'Unknown format: {fmt}')
        print(f'Available: {", ".join(FORMATS.keys())}, all')
        sys.exit(1)

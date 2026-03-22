"""
Invoke tasks for the Kindle dictionary project.

Usage:
    venv/bin/invoke --list          # show all tasks
    venv/bin/invoke build           # generate HTML + build .mobi
    venv/bin/invoke deploy          # build + copy to Kindle
    venv/bin/invoke import-hu       # import Hungarian from all sources
"""

import os
import shutil

from invoke import task

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
KINDLEGEN = '/Applications/Kindle Previewer 3.app/Contents/lib/fc/bin/kindlegen'
KINDLE_DICT_DIR = '/Volumes/Kindle/documents/dictionaries'


@task
def generate(c, lang='nl'):
    """Generate HTML files and OPF from dictionary JSON."""
    c.run(f'venv/bin/python src/generate.py --lang {lang}')


@task
def mobi(c):
    """Build .mobi from generated HTML/OPF using KindleGen."""
    opf = os.path.join(BUILD_DIR, 'dict.opf')
    if not os.path.exists(opf):
        print('No dict.opf found — run `invoke generate` first.')
        return
    c.run(f'"{KINDLEGEN}" {opf} -o dict.mobi')


@task
def build(c, lang='nl'):
    """Generate HTML + build .mobi (full pipeline)."""
    generate(c, lang=lang)
    mobi(c)


@task
def copy(c):
    """Copy dict.mobi to connected Kindle."""
    src = os.path.join(BUILD_DIR, 'dict.mobi')
    if not os.path.exists(src):
        print('No dict.mobi found — run `invoke build` first.')
        return
    if not os.path.isdir(KINDLE_DICT_DIR):
        print(f'Kindle not found at {KINDLE_DICT_DIR} — is it connected?')
        return
    dst = os.path.join(KINDLE_DICT_DIR, 'dict.mobi')
    shutil.copy2(src, dst)
    src_size = os.path.getsize(src)
    dst_size = os.path.getsize(dst)
    if src_size == dst_size:
        print(f'Copied dict.mobi ({src_size / 1024 / 1024:.1f}MB) to Kindle.')
    else:
        print(f'WARNING: size mismatch! src={src_size} dst={dst_size}')


@task
def deploy(c, lang='nl'):
    """Build and copy to Kindle in one step."""
    build(c, lang=lang)
    copy(c)


@task(name='import-wiktionary')
def import_wiktionary(c):
    """Import entries from Dutch Wiktionary dump."""
    c.run('venv/bin/python src/import_wiktionary.py')


@task(name='import-hu-wiktionary')
def import_hu_wiktionary(c):
    """Import Hungarian translations from raw Wiktionary extract."""
    c.run('venv/bin/python src/import_hu_from_wiktionary.py')


@task(name='import-hu-opensub')
def import_hu_opensub(c):
    """Import Hungarian translations from OpenSubtitles corpus."""
    c.run('venv/bin/python src/import_opensub.py')


@task(name='import-hu')
def import_hu(c):
    """Import Hungarian from all sources (Wiktionary + OpenSubtitles)."""
    import_hu_wiktionary(c)
    import_hu_opensub(c)


@task
def serve(c):
    """Start the web server."""
    c.run('venv/bin/python src/server.py')


@task
def stats(c):
    """Show dictionary statistics."""
    c.run('''venv/bin/python -c "
import json, os
for lang_dir in sorted(os.listdir('dictionary')):
    d = os.path.join('dictionary', lang_dir)
    if not os.path.isdir(d):
        continue
    total = 0
    trans_langs = {}
    for f in os.listdir(d):
        if not f.endswith('.json'):
            continue
        with open(os.path.join(d, f), 'r') as fh:
            entries = json.load(fh)
        total += len(entries)
        for e in entries:
            for tl in e.get('translations', {}):
                trans_langs[tl] = trans_langs.get(tl, 0) + 1
    tl_str = ', '.join(f'{l}: {c}' for l, c in sorted(trans_langs.items(), key=lambda x: -x[1]))
    print(f'{lang_dir}: {total:,} entries ({tl_str})')
"''')

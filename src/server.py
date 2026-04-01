"""
Web server for the multilingual dictionary.

Provides a UI for searching, browsing, and adding words across all language dictionaries.
Loads YAML files lazily on first access for fast startup.

Usage:
    cd src && ../venv/bin/python server.py
"""

import atexit
import logging
import os
import json
import tempfile
from flask import Flask, jsonify, render_template, request, send_file

from migrate import (
    parse_file,
    is_expression,
    find_key_word,
    first_letter,
    letter_for_entry,
    save_dict,
)

logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary')

app = Flask(__name__)

# S3 sync (enabled when S3_BUCKET env var is set)
_s3_sync = None
if os.environ.get('S3_BUCKET'):
    from s3_sync import S3Sync
    _s3_sync = S3Sync(DICT_DIR)
    _s3_sync.download_all()
    _s3_sync.start_hourly_check()
    atexit.register(_s3_sync.stop)

# Lazy cache: { 'nl': { 'a': [entries...], ... }, 'en': { ... } }
_cache = {}
# Track which (lang, letter) pairs are loaded
_loaded = set()


def discover_languages():
    """Find all language directories."""
    langs = []
    for name in os.listdir(DICT_DIR):
        if os.path.isdir(os.path.join(DICT_DIR, name)):
            langs.append(name)
    return langs


def discover_letters(lang):
    """Find all letter JSON files for a language."""
    lang_dir = os.path.join(DICT_DIR, lang)
    letters = []
    for filename in os.listdir(lang_dir):
        if filename.endswith('.json'):
            letters.append(filename.replace('.json', ''))
    return letters


def get_entries(lang, letter):
    """Get entries for a language+letter, loading from disk if needed."""
    key = (lang, letter)
    if key not in _loaded:
        if lang not in _cache:
            _cache[lang] = {}
        json_path = os.path.join(DICT_DIR, lang, f'{letter}.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            _cache[lang][letter] = entries if entries else []
        else:
            _cache[lang][letter] = []
        _loaded.add(key)
    return _cache.get(lang, {}).get(letter, [])


def get_all_entries(lang):
    """Get all entries for a language, loading any unloaded letters."""
    for letter in discover_letters(lang):
        get_entries(lang, letter)
    return _cache.get(lang, {})


def invalidate(lang, letter):
    """Remove a cached letter so it reloads from disk next time."""
    _loaded.discard((lang, letter))
    if lang in _cache:
        _cache[lang].pop(letter, None)


def get_stats():
    """Count total words, expressions, and language coverage per dictionary."""
    result = {}
    for lang in discover_languages():
        total = 0
        expressions = 0
        trans_langs = {}
        for letter in discover_letters(lang):
            for entry in get_entries(lang, letter):
                total += 1
                if 'expression_of' in entry:
                    expressions += 1
                for tl in entry.get('translations', {}):
                    trans_langs[tl] = trans_langs.get(tl, 0) + 1
        result[lang] = {
            'total': total,
            'words': total - expressions,
            'expressions': expressions,
            'translation_languages': trans_langs,
        }
    return result


def get_word_index(lang):
    """Build a set of existing words for a language dictionary."""
    words = set()
    for letter in discover_letters(lang):
        for entry in get_entries(lang, letter):
            words.add(entry['word'].lower())
    return words


def save_letter(lang, letter):
    """Write a single letter file back to disk and schedule S3 upload."""
    entries = _cache.get(lang, {}).get(letter, [])
    entries.sort(key=lambda e: e['word'].lower())
    lang_dir = os.path.join(DICT_DIR, lang)
    os.makedirs(lang_dir, exist_ok=True)
    save_dict(entries, os.path.join(lang_dir, f'{letter}.json'))
    if _s3_sync:
        _s3_sync.mark_dirty(lang, letter)


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stats')
def stats():
    return jsonify(get_stats())


@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip().lower()
    lang = request.args.get('lang', '')  # empty = search all
    if not query:
        return jsonify([])

    results = []
    seen = set()

    langs_to_search = [lang] if lang and lang in discover_languages() else discover_languages()

    # Determine which letters to search based on query
    # For short queries, search only matching letter files first
    query_letter = first_letter(query) if query else None

    for search_lang in langs_to_search:
        letters = discover_letters(search_lang)
        # Search the matching letter first for faster results
        if query_letter and query_letter in letters:
            letters = [query_letter] + [l for l in letters if l != query_letter]

        for letter in letters:
            for entry in get_entries(search_lang, letter):
                entry_id = (search_lang, id(entry))
                if entry_id in seen:
                    continue
                matched = False
                if query in entry['word'].lower():
                    matched = True
                if not matched:
                    for tl, trans in entry.get('translations', {}).items():
                        for d in trans.get('definitions', []):
                            if query in d.get('text', '').lower():
                                matched = True
                                break
                        if matched:
                            break
                if matched:
                    seen.add(entry_id)
                    result = dict(entry)
                    result['_lang'] = search_lang
                    results.append(result)
                    if len(results) >= 50:
                        break
            if len(results) >= 50:
                break
        if len(results) >= 50:
            break

    # Sort: exact match first, then starts-with, then contains
    def sort_key(e):
        w = e['word'].lower()
        if w == query:
            return (0, w)
        elif w.startswith(query):
            return (1, w)
        else:
            return (2, w)
    results.sort(key=sort_key)
    return jsonify(results)


@app.route('/api/import', methods=['POST'])
def import_words():
    data = request.json
    text = data.get('text', '')
    source = data.get('source', 'web-import').strip() or 'web-import'
    lang = data.get('lang', 'nl')
    target_lang = data.get('target_lang', 'hu')

    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(text)
        tmpfile = f.name

    try:
        new_entries = parse_file(tmpfile, source_name=source, target_lang=target_lang)
    finally:
        os.unlink(tmpfile)

    if not new_entries:
        return jsonify({'added': 0, 'skipped': 0, 'message': 'No valid words found in input.'})

    existing_words = get_word_index(lang)
    if lang not in _cache:
        _cache[lang] = {}

    added = 0
    merged = 0
    skipped = 0
    updated_letters = set()

    # Build word->entry index for merging
    word_to_entry = {}
    for letter in discover_letters(lang):
        for entry in get_entries(lang, letter):
            word_to_entry[entry['word'].lower()] = entry

    for entry in new_entries:
        word_key = entry['word'].lower()
        if word_key in existing_words:
            # Try to merge translations
            existing_entry = word_to_entry.get(word_key)
            if existing_entry:
                changed = False
                if 'translations' not in existing_entry:
                    existing_entry['translations'] = {}
                for lang_code, trans_data in entry.get('translations', {}).items():
                    if lang_code not in existing_entry['translations']:
                        # Language not present yet — add whole block
                        existing_entry['translations'][lang_code] = trans_data
                        changed = True
                    else:
                        # Language exists — merge definitions
                        existing_defs = existing_entry['translations'][lang_code].get('definitions', [])
                        existing_texts = [d['text'].lower() for d in existing_defs]
                        for new_def in trans_data.get('definitions', []):
                            if new_def['text'].lower() in existing_texts:
                                # Same translation — bump quality +1, max 5
                                for d in existing_defs:
                                    if d['text'].lower() == new_def['text'].lower():
                                        current = d.get('quality', 1)
                                        if current < 5:
                                            d['quality'] = current + 1
                                            changed = True
                                        break
                            else:
                                # Different translation — add as new definition
                                existing_defs.append(new_def)
                                changed = True
                if changed:
                    merged += 1
                    letter = letter_for_entry(entry)
                    updated_letters.add(letter)
                else:
                    skipped += 1
            else:
                skipped += 1
        else:
            letter = letter_for_entry(entry)
            if letter not in _cache[lang]:
                _cache[lang][letter] = []
                _loaded.add((lang, letter))
            _cache[lang][letter].append(entry)
            word_to_entry[word_key] = entry
            existing_words.add(word_key)
            updated_letters.add(letter)
            added += 1

    for letter in updated_letters:
        save_letter(lang, letter)

    parts = []
    if added:
        parts.append(f'Added {added} new words')
    if merged:
        parts.append(f'merged {merged} translations')
    if skipped:
        parts.append(f'skipped {skipped}')
    message = f'{", ".join(parts)} in {lang} dictionary.' if parts else 'No changes.'

    return jsonify({
        'added': added,
        'merged': merged,
        'skipped': skipped,
        'message': message,
    })


@app.route('/api/download')
def download():
    lang = request.args.get('lang', 'nl')
    mobi_path = os.path.join(PROJECT_ROOT, f'dict-{lang}.mobi')
    if not os.path.exists(mobi_path):
        mobi_path = os.path.join(PROJECT_ROOT, 'dict.mobi')
    if os.path.exists(mobi_path):
        return send_file(mobi_path, as_attachment=True, download_name=f'{lang}-dictionary.mobi')
    return jsonify({'error': 'Dictionary file not found. Run generate.py first.'}), 404


@app.route('/api/languages')
def languages():
    return jsonify(discover_languages())


# --- Start ---

if __name__ == '__main__':
    langs = discover_languages()
    print(f'Found {len(langs)} language(s): {", ".join(langs)}')
    print(f'Lazy loading enabled — YAML files loaded on first access')
    app.run(debug=True, port=5333)

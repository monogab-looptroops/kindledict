"""
Web server for the multilingual dictionary.

Provides a UI for searching, browsing, and adding words across all language dictionaries.

Usage:
    cd src && ../venv/bin/python server.py
"""

import os
import tempfile
import yaml
from flask import Flask, jsonify, render_template, request, send_file

from migrate import (
    parse_file,
    is_expression,
    find_key_word,
    first_letter,
    letter_for_entry,
    save_yaml,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary')

app = Flask(__name__)

# In-memory: { 'nl': { 'a': [entries...], ... }, 'en': { ... } }
dictionaries = {}


def load_dictionaries():
    """Load all language dictionaries into memory."""
    global dictionaries
    dictionaries = {}
    for lang in os.listdir(DICT_DIR):
        lang_dir = os.path.join(DICT_DIR, lang)
        if not os.path.isdir(lang_dir):
            continue
        dictionaries[lang] = {}
        for filename in os.listdir(lang_dir):
            if not filename.endswith('.yaml') or filename == 'meta.yaml':
                continue
            letter = filename.replace('.yaml', '')
            filepath = os.path.join(lang_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                entries = yaml.safe_load(f)
            if entries:
                dictionaries[lang][letter] = entries


def get_stats():
    """Count total words, expressions, and language coverage per dictionary."""
    result = {}
    for lang, by_letter in dictionaries.items():
        total = 0
        expressions = 0
        trans_langs = {}
        for entries in by_letter.values():
            for entry in entries:
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
    by_letter = dictionaries.get(lang, {})
    return {entry['word'].lower() for entries in by_letter.values() for entry in entries}


def save_letter(lang, letter):
    """Write a single letter file back to disk."""
    entries = dictionaries.get(lang, {}).get(letter, [])
    entries.sort(key=lambda e: e['word'].lower())
    lang_dir = os.path.join(DICT_DIR, lang)
    os.makedirs(lang_dir, exist_ok=True)
    save_yaml(entries, os.path.join(lang_dir, f'{letter}.yaml'))


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

    langs_to_search = [lang] if lang and lang in dictionaries else list(dictionaries.keys())

    for search_lang in langs_to_search:
        for entries in dictionaries[search_lang].values():
            for entry in entries:
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

    results.sort(key=lambda e: e['word'].lower())
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
    if lang not in dictionaries:
        dictionaries[lang] = {}

    added = 0
    skipped = 0
    updated_letters = set()

    for entry in new_entries:
        if entry['word'].lower() in existing_words:
            skipped += 1
            continue
        letter = letter_for_entry(entry)
        if letter not in dictionaries[lang]:
            dictionaries[lang][letter] = []
        dictionaries[lang][letter].append(entry)
        existing_words.add(entry['word'].lower())
        updated_letters.add(letter)
        added += 1

    for letter in updated_letters:
        save_letter(lang, letter)

    return jsonify({
        'added': added,
        'skipped': skipped,
        'message': f'Added {added} new words to {lang} dictionary, skipped {skipped} duplicates.',
    })


@app.route('/api/download')
def download():
    lang = request.args.get('lang', 'nl')
    mobi_path = os.path.join(PROJECT_ROOT, f'dict-{lang}.mobi')
    if not os.path.exists(mobi_path):
        # Fallback to old name
        mobi_path = os.path.join(PROJECT_ROOT, 'dict.mobi')
    if os.path.exists(mobi_path):
        return send_file(mobi_path, as_attachment=True, download_name=f'{lang}-dictionary.mobi')
    return jsonify({'error': 'Dictionary file not found. Run generate.py first.'}), 404


@app.route('/api/languages')
def languages():
    return jsonify(list(dictionaries.keys()))


# --- Start ---

if __name__ == '__main__':
    load_dictionaries()
    stats_data = get_stats()
    for lang, s in stats_data.items():
        print(f'  {lang}: {s["total"]} entries ({s["words"]} words, {s["expressions"]} expressions)')
    app.run(debug=True, port=5333)

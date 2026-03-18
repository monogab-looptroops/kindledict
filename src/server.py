"""
Web server for the multilingual Dutch dictionary.

Provides a UI for searching, browsing, and adding words.

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
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(PROJECT_ROOT, 'dictionary')

app = Flask(__name__)

# In-memory dictionary: { 'a': [entries...], 'b': [entries...], ... }
dictionary = {}


def load_dictionary():
    """Load all YAML dictionary files into memory."""
    global dictionary
    dictionary = {}
    for filename in os.listdir(DICT_DIR):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue
        letter = filename.replace('.yaml', '')
        filepath = os.path.join(DICT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f)
        if entries:
            dictionary[letter] = entries


def get_stats():
    """Count total words, expressions, and language coverage."""
    total = 0
    expressions = 0
    langs = {}
    for entries in dictionary.values():
        for entry in entries:
            total += 1
            if 'expression_of' in entry:
                expressions += 1
            for lang in entry.get('translations', {}):
                langs[lang] = langs.get(lang, 0) + 1
    return {
        'total': total,
        'words': total - expressions,
        'expressions': expressions,
        'languages': langs,
    }


def get_word_index():
    """Build a set of existing words (lowercased) for duplicate detection."""
    return {entry['word'].lower() for entries in dictionary.values() for entry in entries}


def save_letter(letter):
    """Write a single letter file back to disk."""
    entries = dictionary.get(letter, [])
    entries.sort(key=lambda e: e['word'].lower())
    outfile = os.path.join(DICT_DIR, f'{letter}.yaml')
    with open(outfile, 'w', encoding='utf-8') as f:
        yaml.dump(
            entries,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )


def convert_old_entry_to_new(entry, source):
    """Convert an old-format import entry to the new multilingual format."""
    hu_defs = []
    hu_examples = []
    for meaning in entry.get('meanings', []):
        defn = meaning.get('definition', '')
        if defn:
            hu_def = {'text': defn, 'quality': 3}
            if meaning.get('english'):
                hu_def['english_hint'] = meaning['english']
            hu_defs.append(hu_def)
        for ex in meaning.get('examples', []):
            hu_examples.append({'nl': ex.get('nl', ''), 'tr': ex.get('hu', '')})

    translations = {}
    if hu_defs:
        hu_trans = {'definitions': hu_defs}
        if hu_examples:
            hu_trans['examples'] = hu_examples
        translations['hu'] = hu_trans

    new_entry = {
        'word': entry['word'],
        'ipa': entry.get('ipa', ''),
        'pos': entry.get('pos', ''),
        'translations': translations,
        'source': source,
    }
    if 'expression_of' in entry:
        new_entry['expression_of'] = entry['expression_of']
    return new_entry


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
    if not query:
        return jsonify([])

    results = []
    seen = set()
    for entries in dictionary.values():
        for entry in entries:
            if id(entry) in seen:
                continue
            matched = False
            # Match on word
            if query in entry['word'].lower():
                matched = True
            # Match on translations
            if not matched:
                for lang, trans in entry.get('translations', {}).items():
                    for d in trans.get('definitions', []):
                        if query in d.get('text', '').lower():
                            matched = True
                            break
                    if matched:
                        break
            if matched:
                seen.add(id(entry))
                results.append(entry)
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

    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400

    # Write to temp file and parse (old format)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(text)
        tmpfile = f.name

    try:
        old_entries = parse_file(tmpfile, source_name=source)
    finally:
        os.unlink(tmpfile)

    if not old_entries:
        return jsonify({'added': 0, 'skipped': 0, 'message': 'No valid words found in input.'})

    existing_words = get_word_index()
    added = 0
    skipped = 0
    updated_letters = set()

    for old_entry in old_entries:
        if old_entry['word'].lower() in existing_words:
            skipped += 1
            continue
        new_entry = convert_old_entry_to_new(old_entry, source)
        letter = letter_for_entry(new_entry)
        if letter not in dictionary:
            dictionary[letter] = []
        dictionary[letter].append(new_entry)
        existing_words.add(new_entry['word'].lower())
        updated_letters.add(letter)
        added += 1

    # Persist changed files
    for letter in updated_letters:
        save_letter(letter)

    return jsonify({
        'added': added,
        'skipped': skipped,
        'message': f'Added {added} new words, skipped {skipped} duplicates.',
    })


@app.route('/api/download')
def download():
    mobi_path = os.path.join(PROJECT_ROOT, 'dict.mobi')
    if os.path.exists(mobi_path):
        return send_file(mobi_path, as_attachment=True, download_name='nl-dictionary.mobi')
    return jsonify({'error': 'Dictionary file not found. Run generate.py first.'}), 404


# --- Start ---

if __name__ == '__main__':
    load_dictionary()
    s = get_stats()
    print(f'Dictionary loaded: {s["total"]} entries ({s["words"]} words, {s["expressions"]} expressions)')
    print(f'Languages: {s["languages"]}')
    app.run(debug=True, port=5333)

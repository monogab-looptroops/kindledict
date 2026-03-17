"""
Web server for the Dutch-Hungarian dictionary.

Provides a UI for searching, browsing, and adding words.

Usage:
    venv/bin/python src/server.py
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
    """Count total words and expressions."""
    total = 0
    expressions = 0
    for entries in dictionary.values():
        for entry in entries:
            total += 1
            if 'expression_of' in entry:
                expressions += 1
    return {'total': total, 'words': total - expressions, 'expressions': expressions}


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
            # Match on definitions
            if not matched:
                for m in entry['meanings']:
                    if query in m.get('definition', '').lower():
                        matched = True
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

    # Write to temp file and parse
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(text)
        tmpfile = f.name

    try:
        new_entries = parse_file(tmpfile, source_name=source)
    finally:
        os.unlink(tmpfile)

    if not new_entries:
        return jsonify({'added': 0, 'skipped': 0, 'message': 'No valid words found in input.'})

    existing_words = get_word_index()
    added = 0
    skipped = 0
    updated_letters = set()

    for entry in new_entries:
        if entry['word'].lower() in existing_words:
            skipped += 1
            continue
        letter = letter_for_entry(entry)
        if letter not in dictionary:
            dictionary[letter] = []
        dictionary[letter].append(entry)
        existing_words.add(entry['word'].lower())
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
        return send_file(mobi_path, as_attachment=True, download_name='nl-hu-dictionary.mobi')
    return jsonify({'error': 'Dictionary file not found. Run generate.py first.'}), 404


# --- Start ---

if __name__ == '__main__':
    load_dictionary()
    stats = get_stats()
    print(f'Dictionary loaded: {stats["total"]} entries ({stats["words"]} words, {stats["expressions"]} expressions)')
    app.run(debug=True, port=5333)

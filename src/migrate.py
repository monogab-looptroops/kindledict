"""
Import new words into the structured YAML dictionary.

- Parses plain-text word files (word - translation format)
- Merges new entries into existing dictionary/<lang>/*.yaml files
- Skips words that already exist in the dictionary
- Preserves all manual edits

Usage:
    python src/migrate.py                       # import all from words/ into nl
    python src/migrate.py words/new-book        # import a specific file into nl
    python src/migrate.py --lang en words/file  # import into English dictionary
"""

import os
import re
import sys
import yaml
from functools import reduce
from collections import defaultdict


def parse_file(filename, source_name, target_lang='hu'):
    """Parse a word file into structured dictionary entries."""
    # Try utf-8 first, fall back to latin-1
    for enc in ['utf-8', 'latin-1']:
        try:
            with open(filename, encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    entries = []
    for line in lines:
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue

        # Check if this is an example line: [word - translation] or <...> or (e.g. ...)
        is_example = line.startswith('[') and line.endswith(']')
        if is_example:
            line = line.strip('[]')

        is_angle_example = line.startswith('<') and line.endswith('>')
        if is_angle_example:
            is_example = True
            line = line.strip('<>')

        is_paren_example = line.startswith('(e.g.')
        if is_paren_example:
            is_example = True
            line = line.strip('()')
            line = re.sub(r'^e\.g\.\s*', '', line)

        # Split on first " - " to separate source and target
        ws = line.split(' - ', 1)
        if len(ws) < 2:
            ws = line.split('-')
            if len(ws) > 2:
                wsr = [ws[0], reduce(lambda a, b: a + '-' + b, ws[1:])]
                ws = wsr

        ws = [w.strip() for w in ws]

        if len(ws) < 2 or ws[0] == '' or ws[1] == '':
            continue

        src_text = ws[0]
        tgt_text = ws[1]

        if is_example:
            # Attach example to the last entry
            if entries:
                trans = entries[-1]['translations'].get(target_lang, {})
                if 'examples' not in trans:
                    trans['examples'] = []
                trans['examples'].append({
                    'nl': src_text,
                    'tr': tgt_text,
                })
            continue

        # Extract <english> hint if present
        english_match = re.search(r'<(.+?)>\s*$', tgt_text)
        english_hint = None
        if english_match:
            english_hint = english_match.group(1)
            tgt_text = tgt_text[:english_match.start()].strip()
            tgt_text = tgt_text.rstrip(',').strip()

        # Build multilingual entry
        tgt_def = {'text': tgt_text, 'quality': 3}
        if english_hint:
            tgt_def['english_hint'] = english_hint

        entry = {
            'word': src_text,
            'ipa': '',
            'pos': '',
            'translations': {
                target_lang: {
                    'definitions': [tgt_def],
                },
            },
            'source': source_name,
        }

        if is_expression(src_text):
            entry['expression_of'] = find_key_word(src_text)

        entries.append(entry)

    return entries


# Common function words to skip when finding the key word of an expression
STOP_WORDS = {
    # Dutch
    'de', 'het', 'een',
    'aan', 'bij', 'door', 'in', 'met', 'na', 'naar', 'om', 'op', 'over',
    'per', 'te', 'tot', 'uit', 'van', 'via', 'voor', 'zonder', 'tegen',
    'onder', 'tussen', 'langs', 'rond', 'rondom', 'sinds', 'tijdens',
    'je', 'jij', 'hij', 'zij', 'ze', 'wij', 'we', 'ik', 'me', 'mij',
    'zich', 'zijn', 'haar', 'hun', 'ons', 'dit', 'dat', 'deze', 'die',
    'wat', 'wie', 'welk', 'welke', 'iets', 'niets', 'iemand', 'niemand',
    'elkaar', 'zichzelf',
    'en', 'of', 'maar', 'want', 'dus', 'als', 'dan', 'nog', 'al', 'ook',
    'niet', 'geen', 'wel', 'er', 'daar', 'hier', 'waar',
    'andere', 'ander', 'alle', 'veel', 'meer', 'hele', 'heel',
    'zo', 'te', 'ten',
    # English
    'the', 'a', 'an', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with',
    'from', 'is', 'are', 'was', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'may', 'might',
    'can', 'could', 'must', 'not', 'no', 'nor', 'and', 'but', 'or', 'so',
    'if', 'that', 'this', 'these', 'those', 'it', 'its', 'my', 'your',
    'his', 'her', 'our', 'their', 'who', 'whom', 'which', 'what',
}


def find_key_word(phrase):
    """Find the most meaningful word in a multi-word expression."""
    words = phrase.lower().split()
    for w in words:
        if w not in STOP_WORDS and w[0].isalpha():
            return w
    return words[-1]


def is_expression(word):
    """Check if an entry is a multi-word expression rather than a single word."""
    words = word.strip().split()
    # Filter out articles + noun
    if len(words) == 2 and words[0].lower() in ('de', 'het', 'een', 'the', 'a', 'an'):
        return False
    return len(words) > 1


def first_letter(word):
    """Get the first letter of a word, normalized to lowercase."""
    w = word.lower().strip()
    for ch in w:
        if ch.isalpha():
            return ch
    words = w.split()
    for word in words:
        for ch in word:
            if ch.isalpha():
                return ch
    return '_'


def letter_for_entry(entry):
    """Determine which letter file an entry belongs in."""
    if 'expression_of' in entry:
        return first_letter(entry['expression_of'])
    return first_letter(entry['word'])


def save_yaml(entries, filepath):
    """Write entries to a YAML file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(
            entries, f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )


def load_existing_dictionary(dict_dir):
    """Load all existing YAML dictionary files into a dict keyed by letter."""
    by_letter = {}
    if not os.path.exists(dict_dir):
        return by_letter
    for filename in os.listdir(dict_dir):
        if not filename.endswith('.yaml') or filename == 'meta.yaml':
            continue
        letter = filename.replace('.yaml', '')
        filepath = os.path.join(dict_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            entries = yaml.safe_load(f)
        if entries:
            by_letter[letter] = entries
    return by_letter


def build_word_index(by_letter):
    """Build a dict of existing words (lowercased) -> entry for merge support."""
    existing = {}
    for entries in by_letter.values():
        for entry in entries:
            existing[entry['word'].lower()] = entry
    return existing


def migrate(files=None, lang='nl', target_lang='hu'):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    words_dir = os.path.join(project_root, 'words')
    dict_dir = os.path.join(project_root, 'dictionary', lang)
    os.makedirs(dict_dir, exist_ok=True)

    # Load existing dictionary
    by_letter = load_existing_dictionary(dict_dir)
    existing_words = build_word_index(by_letter)
    print(f'Existing {lang} dictionary: {len(existing_words)} words')

    # Determine which files to import
    if files:
        file_list = files
    else:
        file_list = []
        for filename in sorted(os.listdir(words_dir)):
            filepath = os.path.join(words_dir, filename)
            if os.path.isdir(filepath) or filename.startswith('.'):
                continue
            file_list.append(filepath)

    # Parse new words
    new_entries = []
    merged = 0
    skipped = 0
    for filepath in file_list:
        source_name = os.path.basename(filepath)
        entries = parse_file(filepath, source_name, target_lang=target_lang)
        file_new = 0
        file_merged = 0
        for entry in entries:
            word_key = entry['word'].lower()
            if word_key in existing_words:
                # Word exists — merge new translations into existing entry
                existing_entry = existing_words[word_key]
                new_translations = entry.get('translations', {})
                changed = False
                for lang_code, trans_data in new_translations.items():
                    if lang_code not in existing_entry.get('translations', {}):
                        if 'translations' not in existing_entry:
                            existing_entry['translations'] = {}
                        existing_entry['translations'][lang_code] = trans_data
                        changed = True
                if changed:
                    file_merged += 1
                    merged += 1
                else:
                    skipped += 1
            else:
                new_entries.append(entry)
                existing_words[entry['word'].lower()] = entry
                file_new += 1
        status = f'{file_new} new'
        if file_merged:
            status += f', {file_merged} merged'
        if skipped:
            status += f', {skipped} skipped (already has translation)'
        print(f'  {source_name}: {status}')

    if not new_entries and not merged:
        print(f'\nNo changes. ({skipped} already had translations)')
        return

    # Add new entries into dictionary
    for entry in new_entries:
        letter = letter_for_entry(entry)
        if letter not in by_letter:
            by_letter[letter] = []
        by_letter[letter].append(entry)

    # Sort and write updated files (both new and merged entries need saving)
    updated_letters = {letter_for_entry(e) for e in new_entries}
    if merged:
        updated_letters = set(by_letter.keys())
    for letter in sorted(updated_letters):
        entries = by_letter[letter]
        entries.sort(key=lambda e: e['word'].lower())
        save_yaml(entries, os.path.join(dict_dir, f'{letter}.yaml'))
        print(f'  Updated {letter}.yaml: {len(entries)} entries')

    # Write meta.yaml if it doesn't exist
    meta_path = os.path.join(dict_dir, 'meta.yaml')
    if not os.path.exists(meta_path):
        meta = {
            'language': lang,
            'title': f'{lang} Multilingual Dictionary',
            'author': 'Gabor Monostori',
            'version': 2.0,
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    total = sum(len(entries) for entries in by_letter.values())
    print(f'\nDone. Added {len(new_entries)} new, merged {merged} existing, skipped {skipped}.')
    print(f'{lang} dictionary total: {total} words')


if __name__ == '__main__':
    # Parse --lang flag
    args = sys.argv[1:]
    lang = 'nl'
    target_lang = 'hu'
    if '--lang' in args:
        idx = args.index('--lang')
        lang = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
        # Default target language based on source
        if lang == 'en':
            target_lang = 'hu'

    if args:
        files = [os.path.abspath(f) for f in args]
        migrate(files, lang=lang, target_lang=target_lang)
    else:
        migrate(lang=lang, target_lang=target_lang)

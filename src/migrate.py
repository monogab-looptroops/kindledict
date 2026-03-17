"""
Import new words from words/ into the structured YAML dictionary.

- Parses plain-text word files from words/
- Merges new entries into existing dictionary/*.yaml files
- Skips words that already exist in the dictionary
- Preserves all manual edits (IPA, pos, meanings, etc.)

Usage:
    python src/migrate.py                  # import all files from words/
    python src/migrate.py words/new-book   # import a specific file
"""

import os
import re
import sys
import yaml
from functools import reduce
from collections import defaultdict


def parse_file(filename, source_name):
    """Parse a legacy word file into structured dictionary entries."""
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

        # Check if this is an example line: [dutch - hungarian] or <dutch - hungarian> or (e.g. ...)
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

        # Split on first " - " to separate nl and hu
        ws = line.split(' - ', 1)
        if len(ws) < 2:
            # Try splitting on just "-" as fallback
            ws = line.split('-')
            if len(ws) > 2:
                wsr = [ws[0], reduce(lambda a, b: a + '-' + b, ws[1:])]
                ws = wsr

        ws = [w.strip() for w in ws]

        if len(ws) < 2 or ws[0] == '' or ws[1] == '':
            continue

        nl_text = ws[0]
        hu_text = ws[1]

        if is_example:
            # Attach example to the last entry
            if entries:
                if 'examples' not in entries[-1]['meanings'][0]:
                    entries[-1]['meanings'][0]['examples'] = []
                entries[-1]['meanings'][0]['examples'].append({
                    'nl': nl_text,
                    'hu': hu_text,
                })
            continue

        # Extract <english> hint if present
        english_match = re.search(r'<(.+?)>\s*$', hu_text)
        english_hint = None
        if english_match:
            english_hint = english_match.group(1)
            hu_text = hu_text[:english_match.start()].strip()
            # Remove trailing comma if any
            hu_text = hu_text.rstrip(',').strip()

        entry = {
            'word': nl_text,
            'ipa': '',
            'pos': '',
            'meanings': [
                {
                    'definition': hu_text,
                }
            ],
            'source': source_name,
        }

        if is_expression(nl_text):
            entry['expression_of'] = find_key_word(nl_text)

        if english_hint:
            entry['meanings'][0]['english'] = english_hint

        entries.append(entry)

    return entries


# Dutch function words to skip when finding the key word of an expression
DUTCH_STOP_WORDS = {
    # articles
    'de', 'het', 'een',
    # prepositions
    'aan', 'bij', 'door', 'in', 'met', 'na', 'naar', 'om', 'op', 'over',
    'per', 'te', 'tot', 'uit', 'van', 'via', 'voor', 'zonder', 'tegen',
    'onder', 'tussen', 'langs', 'rond', 'rondom', 'sinds', 'tijdens',
    # pronouns
    'je', 'jij', 'hij', 'zij', 'ze', 'wij', 'we', 'ik', 'me', 'mij',
    'zich', 'zijn', 'haar', 'hun', 'ons', 'dit', 'dat', 'deze', 'die',
    'wat', 'wie', 'welk', 'welke', 'iets', 'niets', 'iemand', 'niemand',
    'elkaar', 'zichzelf',
    # conjunctions / adverbs
    'en', 'of', 'maar', 'want', 'dus', 'als', 'dan', 'nog', 'al', 'ook',
    'niet', 'geen', 'wel', 'er', 'daar', 'hier', 'waar',
    # other common function words
    'andere', 'ander', 'alle', 'veel', 'meer', 'hele', 'heel',
    'zo', 'te', 'ten',
}


def find_key_word(phrase):
    """Find the most meaningful word in a multi-word expression."""
    words = phrase.lower().split()
    # Pick the first non-stop word that starts with a letter
    for w in words:
        if w not in DUTCH_STOP_WORDS and w[0].isalpha():
            return w
    # Fallback: last word
    return words[-1]


def is_expression(word):
    """Check if an entry is a multi-word expression rather than a single word."""
    words = word.strip().split()
    # Filter out articles + noun (e.g. "het ventiel" = single word with article)
    if len(words) == 2 and words[0] in ('de', 'het', 'een'):
        return False
    return len(words) > 1


def first_letter(word):
    """Get the first letter of a word, normalized to lowercase a-z."""
    w = word.lower().strip()
    for ch in w:
        if ch.isalpha():
            return ch
    # For entries starting with digits, find the key word's letter
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
    """Build a set of existing words (lowercased) for duplicate detection."""
    existing = set()
    for entries in by_letter.values():
        for entry in entries:
            existing.add(entry['word'].lower())
    return existing


def migrate(files=None):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    words_dir = os.path.join(project_root, 'words')
    dict_dir = os.path.join(project_root, 'dictionary')
    os.makedirs(dict_dir, exist_ok=True)

    # Load existing dictionary
    by_letter = load_existing_dictionary(dict_dir)
    existing_words = build_word_index(by_letter)
    print(f'Existing dictionary: {len(existing_words)} words')

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
    skipped = 0
    for filepath in file_list:
        source_name = os.path.basename(filepath)
        entries = parse_file(filepath, source_name)
        file_new = 0
        file_skipped = 0
        for entry in entries:
            if entry['word'].lower() in existing_words:
                file_skipped += 1
                skipped += 1
            else:
                new_entries.append(entry)
                existing_words.add(entry['word'].lower())
                file_new += 1
        status = f'{file_new} new'
        if file_skipped:
            status += f', {file_skipped} skipped (duplicates)'
        print(f'  {source_name}: {status}')

    if not new_entries:
        print(f'\nNo new words to add. ({skipped} duplicates skipped)')
        return

    # Merge new entries into existing dictionary
    for entry in new_entries:
        letter = letter_for_entry(entry)
        if letter not in by_letter:
            by_letter[letter] = []
        by_letter[letter].append(entry)

    # Sort and write updated files
    updated_letters = {letter_for_entry(e) for e in new_entries}
    for letter in sorted(updated_letters):
        entries = by_letter[letter]
        entries.sort(key=lambda e: e['word'].lower())
        outfile = os.path.join(dict_dir, f'{letter}.yaml')
        with open(outfile, 'w', encoding='utf-8') as f:
            yaml.dump(
                entries,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
        print(f'  Updated {letter}.yaml: {len(entries)} entries')

    # Write/update meta.yaml if it doesn't exist
    meta_path = os.path.join(dict_dir, 'meta.yaml')
    if not os.path.exists(meta_path):
        meta = {
            'source_language': 'nl',
            'target_language': 'hu',
            'title': 'Nederlands-Hongaars Woordenschat',
            'author': 'Gabor Monostori',
            'version': 1.0,
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    total = sum(len(entries) for entries in by_letter.values())
    print(f'\nDone. Added {len(new_entries)} new words, skipped {skipped} duplicates.')
    print(f'Dictionary total: {total} words')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Import specific files
        files = [os.path.abspath(f) for f in sys.argv[1:]]
        migrate(files)
    else:
        migrate()

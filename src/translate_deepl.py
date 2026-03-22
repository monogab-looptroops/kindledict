"""
Translate words from stdin or a file via DeepL API.

Reads words (one per line), translates NL→HU, outputs tab-separated pairs.
Saves progress so it can resume after interruption or quota limits.

Usage:
    venv/bin/python src/select_words.py --limit 1000 | venv/bin/python src/translate_deepl.py
    venv/bin/python src/translate_deepl.py < data/batch.txt
    venv/bin/python src/translate_deepl.py < data/batch.txt > data/translated.tsv
    venv/bin/python src/translate_deepl.py --status    # show API usage
"""

import deepl
import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_FILE = os.path.join(PROJECT_ROOT, 'data', 'deepl_progress.json')
ENV_FILE = os.path.join(PROJECT_ROOT, '.env')

BATCH_SIZE = 50


def load_api_key():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith('DEEPL_API_KEY='):
                return line.strip().split('=', 1)[1]
    raise RuntimeError('DEEPL_API_KEY not found in .env')


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'translated': {}}


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, ensure_ascii=False)


def main():
    api_key = load_api_key()
    translator = deepl.Translator(api_key)

    # Status only
    if '--status' in sys.argv:
        usage = translator.get_usage()
        if usage.character.limit:
            remaining = usage.character.limit - usage.character.count
            print(f'Used: {usage.character.count:,} / {usage.character.limit:,} chars')
            print(f'Remaining: {remaining:,} chars')
        return

    # Read words from stdin
    words = [line.strip().split('\t')[0] for line in sys.stdin if line.strip()]
    if not words:
        print('No words provided on stdin.', file=sys.stderr)
        return

    # Load progress — skip already translated
    progress = load_progress()
    already = progress.get('translated', {})
    new_words = [w for w in words if w not in already]

    # Output already-translated words immediately
    for w in words:
        if w in already:
            print(f'{w}\t{already[w]}')

    print(f'Input: {len(words)} words, {len(words) - len(new_words)} cached, {len(new_words)} to translate', file=sys.stderr)

    if not new_words:
        return

    # Check remaining quota
    usage = translator.get_usage()
    if usage.character.limit:
        remaining = usage.character.limit - usage.character.count
        print(f'DeepL remaining: {remaining:,} chars', file=sys.stderr)
    else:
        remaining = 500_000

    chars_used = 0
    translated = 0
    total_batches = (len(new_words) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(new_words), BATCH_SIZE):
        batch = new_words[i:i + BATCH_SIZE]
        batch_chars = sum(len(w) for w in batch)
        batch_num = i // BATCH_SIZE + 1

        if chars_used + batch_chars > remaining - 1000:
            print(f'Stopping: approaching character limit', file=sys.stderr)
            break

        try:
            results = translator.translate_text(batch, source_lang='NL', target_lang='HU')
        except deepl.exceptions.QuotaExceededException:
            print(f'Quota exceeded after {translated} words', file=sys.stderr)
            break
        except Exception as e:
            print(f'Error: {e}', file=sys.stderr)
            break

        for word, result in zip(batch, results):
            hu = result.text
            print(f'{word}\t{hu}')
            print(f'  {word} → {hu}', file=sys.stderr)
            progress['translated'][word] = hu
            translated += 1

        chars_used += batch_chars
        save_progress(progress)

        if batch_num % 20 == 0:
            print(f'  Progress: {translated}/{len(new_words)} ({batch_num}/{total_batches} batches)', file=sys.stderr)
            time.sleep(1)

    print(f'Translated {translated} new words ({chars_used:,} chars)', file=sys.stderr)


if __name__ == '__main__':
    main()

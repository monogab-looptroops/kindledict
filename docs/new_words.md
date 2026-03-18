# Adding New Words

## Quick start

1. Create a plain-text file in `words/` with your new words
2. Run `venv/bin/python3 src/migrate.py` to import them
3. Delete the file from `words/` (the words are now in `dictionary/`)

You can also add words via the web UI at http://localhost:5333 (run `cd src && ../venv/bin/python server.py`).

## Word file format

Each line is a Dutch word or expression followed by its Hungarian translation, separated by ` - `:

```
fiets - bicikli
het ventiel - szelep
kruiperig - szolgalelkű
verstrijken - múlik (az idő)
```

### Examples

Use `[...]` or `<...>` brackets on the line after a word to attach an example sentence:

```
bekommeren - aggódni
[ik ben te moe om me daar om te bekommeren - fáradt vagyok, hogy azon aggódjak]

gelijkmatig - egyenletes
<gelijkmatig druk - egyenletes nyomás>
```

### English hints

Add an English translation in `<...>` at the end of the Hungarian definition:

```
kakkerlak - csótány <cockroach>
krakkemikkig - rozoga <rickety, wobbly>
```

### Comments and blank lines

Lines starting with `#` are ignored. Blank lines are ignored.

```
# words from chapter 3
fiets - bicikli

# kitchen vocabulary
lepel - kanál
```

## Import commands

Import all files from `words/`:

```
venv/bin/python3 src/migrate.py
```

Import a specific file:

```
venv/bin/python3 src/migrate.py words/my-new-book
```

The script will:
- Skip words that already exist in the dictionary (case-insensitive)
- Report how many new words were added and how many duplicates were skipped
- Only update the letter files that received new entries

## Dictionary structure

Words live in `dictionary/a.yaml` through `dictionary/z.yaml`, sorted alphabetically.
Each entry uses the **multilingual format**:

```yaml
- word: bekommeren
  ipa: /bəˈkɔmərə(n)/
  pos: verb
  translations:
    hu:
      definitions:
      - text: aggódni
        quality: 3
        english_hint: worry, bother about smt
      examples:
      - nl: ik ben te moe om me daar om te bekommeren
        tr: fáradt vagyok, hogy azon aggódjak
    en:
      definitions:
      - text: to worry, to concern
        quality: 5
  source: kattenoog
```

### Translation quality

Each definition has a `quality` score (1-5):

| Quality | Meaning | Source |
|---------|---------|--------|
| 1 | Machine translated | LibreTranslate, etc. |
| 2 | Possibly misaligned | Frequency list imports |
| 3 | Human translated | Your word files |
| 4 | Verified by user | Manual review |
| 5 | Authoritative | Wiktionary, etc. |

### Supported languages

| Code | Language |
|------|----------|
| hu | Hungarian |
| en | English |
| es | Spanish |
| nl | Dutch (native definitions) |
| de | German |
| fr | French |

Languages are shown in priority order. If Hungarian is missing, English serves as fallback, then other languages.

### Expressions

Multi-word entries (e.g. "aan de andere kant") are stored under the letter of their key word. They have an `expression_of` field:

```yaml
- word: aan de andere kant
  ipa: ''
  pos: ''
  translations:
    hu:
      definitions:
      - text: a másik oldalon
        quality: 3
  source: mix
  expression_of: kant          # filed under k.yaml, not a.yaml
```

Articles + noun (e.g. "het ventiel") are treated as regular words, not expressions.

## Editing the dictionary

The YAML files in `dictionary/` are the master copy. You can freely edit them to:
- Add or fix translations in any language
- Add IPA pronunciation (`ipa` field)
- Set part of speech (`pos` field)
- Add examples
- Increase quality scores after verification

Your edits are preserved when importing new words — the script only appends, never overwrites.

## Generating the Kindle dictionary

```
cd src && ../venv/bin/python generate.py
```

This produces `content_gen.html` which can be compiled with KindleGen to create `dict.mobi`.
The Kindle dictionary shows all available translations with quality indicators (filled/empty dots).

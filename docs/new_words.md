# Adding New Words

## Quick start

1. Create a plain-text file in `words/` with your new words
2. Run `venv/bin/python3 src/migrate.py` to import them
3. Delete the file from `words/` (the words are now in `dictionary/`)

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

You can also use `(e.g. ...)`:

```
gelijkmatig - egyenletes
(e.g. gelijkmatig druk - egyenletes nyomás)
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

After import, words live in `dictionary/a.yaml` through `dictionary/z.yaml`, sorted alphabetically.

Each entry looks like this:

```yaml
- word: bekommeren
  ipa: ''
  pos: ''
  meanings:
  - definition: aggódni
    examples:
    - nl: ik ben te moe om me daar om te bekommeren
      hu: fáradt vagyok, hogy azon aggódjak
  source: kattenoog
```

### Expressions

Multi-word entries (e.g. "aan de andere kant") are stored under the letter of their key word, not their first word. They have an `expression_of` field:

```yaml
- word: aan de andere kant
  ipa: ''
  pos: ''
  meanings:
  - definition: a másik oldalon
  source: mix
  expression_of: kant          # filed under k.yaml, not a.yaml
```

Articles + noun (e.g. "het ventiel") are treated as regular words, not expressions.

## Editing the dictionary

The YAML files in `dictionary/` are the master copy. You can freely edit them to:
- Add IPA pronunciation (`ipa` field)
- Set part of speech (`pos` field)
- Add alternative meanings (append to `meanings` list)
- Add or edit examples
- Fix definitions

Your edits are preserved when importing new words — the script only appends, never overwrites.

# KindleDict

A web-based multilingual dictionary builder. Add, search, and manage word translations through a browser UI, then export as a Kindle-compatible `.mobi` dictionary for use on e-readers.

## Features

- **Web UI** for searching, browsing, and importing words across multiple languages
- **Smart merging** — adding an existing word appends new translations or boosts quality scores for confirmed ones
- **Kindle export** — generate `.mobi` dictionary files ready for sideloading onto Kindle/e-readers
- **S3 persistence** — dictionary data syncs to AWS S3 with debounced writes (1-minute inactivity trigger + hourly safety check)
- **Multiple import sources** — supports Wiktionary, OpenSubtitles, DeepL, and manual word files

## Run with Docker

### 1. Configure credentials

Copy and fill in `.env.docker`:

```
S3_BUCKET=kindledict
S3_PREFIX=dictionary/
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=eu-central-1
```

### 2. Build and run

```bash
docker compose up --build
```

The app will be available at `http://localhost:5333`.

## Run without Docker

### 1. Set up virtualenv

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the server

```bash
cd src
python server.py
```

To enable S3 sync, export the environment variables before starting:

```bash
export S3_BUCKET=kindledict
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=eu-central-1
cd src
python server.py
```

### 3. Generate Kindle dictionary

```bash
cd src
python generate.py
```

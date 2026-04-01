"""
S3 sync for dictionary files with debounced uploads.

- On startup: downloads all dictionary files from S3
- After changes: waits 60s of inactivity before uploading (debounce)
- Every hour: checks and uploads any pending changes (safety net)
"""

import os
import threading
import time
import logging

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET', 'kindledict')
S3_PREFIX = os.environ.get('S3_PREFIX', 'dictionary/')
DEBOUNCE_SECONDS = 60
HOURLY_CHECK_SECONDS = 3600


class S3Sync:
    def __init__(self, dict_dir):
        self.dict_dir = dict_dir
        self.s3 = boto3.client('s3')
        self._dirty = set()  # set of (lang, letter) that need uploading
        self._lock = threading.Lock()
        self._timer = None
        self._running = True

    def download_all(self):
        """Download all dictionary files from S3 to local disk."""
        paginator = self.s3.get_paginator('list_objects_v2')
        count = 0
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # S3_PREFIX is "dictionary/", key is like "dictionary/nl/a.json"
                rel_path = key[len(S3_PREFIX):]
                if not rel_path:
                    continue
                local_path = os.path.join(self.dict_dir, rel_path)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self.s3.download_file(S3_BUCKET, key, local_path)
                count += 1
        logger.info(f'Downloaded {count} files from s3://{S3_BUCKET}/{S3_PREFIX}')

    def mark_dirty(self, lang, letter):
        """Mark a letter file as needing upload. Resets the debounce timer."""
        logger.info(f'Changed {lang}/{letter}.json — will sync to S3 after {DEBOUNCE_SECONDS}s of inactivity')
        with self._lock:
            self._dirty.add((lang, letter))
            # Reset debounce timer
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        """Upload all dirty files to S3."""
        with self._lock:
            to_upload = list(self._dirty)
            self._dirty.clear()

        for lang, letter in to_upload:
            local_path = os.path.join(self.dict_dir, lang, f'{letter}.json')
            if not os.path.exists(local_path):
                continue
            s3_key = f'{S3_PREFIX}{lang}/{letter}.json'
            try:
                with open(local_path, 'rb') as f:
                    self.s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=f.read())
                logger.info(f'Uploaded {s3_key}')
            except Exception:
                logger.exception(f'Failed to upload {s3_key}')
                # Put it back so the hourly check retries
                with self._lock:
                    self._dirty.add((lang, letter))

    def _hourly_loop(self):
        """Safety net: flush any pending changes every hour."""
        while self._running:
            time.sleep(HOURLY_CHECK_SECONDS)
            if self._dirty:
                logger.info('Hourly check: flushing pending changes')
                self._flush()

    def start_hourly_check(self):
        """Start the background hourly check thread."""
        t = threading.Thread(target=self._hourly_loop, daemon=True)
        t.start()

    def stop(self):
        """Flush remaining changes and stop."""
        self._running = False
        if self._timer:
            self._timer.cancel()
        self._flush()

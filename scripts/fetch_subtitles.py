#!/usr/bin/env python3
"""Fetch English auto-captions for the videos in a channel index or shortlist.

Resumable: videos that already have a transcript, or that are recorded as
permanent failures, are skipped, so the script can be stopped and restarted.

Throttling is the main hazard. YouTube answers sustained parallel requests with
HTTP 429 and a bot check, and the failure surfaces as a *missing caption track*
rather than an error - which silently looks like "this video has no captions".
To keep those apart, errors are allowed to raise (never `ignoreerrors`), and a
429 pauses every worker before anything is written to the failure list.

Input is any JSON file with a `videos` list, so it reads either the full
channel index or the instructional shortlist from 00_select_teaching.py.

Output:
    <out-dir>/<video_id>.txt      timestamped transcript
    <out-dir>/_failures.json      videos that are permanently unavailable

Usage:
    python scripts/fetch_subtitles.py [--workers 3] [--sleep 1.0]
                                      [--cookies-from-browser chrome]
    python scripts/fetch_subtitles.py \
        --index knowledge-base/data/teaching_shortlist.json \
        --out-dir knowledge-base/transcripts
"""

import argparse
import glob
import json
import os
import random
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import yt_dlp

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..')
INDEX = os.path.join(ROOT, 'knowledge-base', 'data', 'daytradewarrior_videos.json')
OUT_DIR = os.path.join(ROOT, 'data', 'subtitles')
RAW_DIR = os.path.join(ROOT, 'data', 'subtitles_raw')
FAIL_PATH = os.path.join(OUT_DIR, '_failures.json')

# Transcripts already fetched for the full channel are reused rather than
# re-requested: every avoided request is one less chance of a bot check.
SEED_DIRS = [os.path.join(ROOT, 'data', 'subtitles')]

# Signatures of a rate limit or bot check. These are transient: the video is
# fine, we are simply asking too fast, so they must never be recorded as
# permanent failures.
THROTTLE_MARKERS = (
    'too many requests',
    'http error 429',
    'sign in to confirm',
    'confirm you',
    'http error 403',
)

_lock = threading.Lock()
_resume_at = 0.0          # wall-clock time before which no worker may request


def is_throttle(msg):
    low = msg.lower()
    return any(m in low for m in THROTTLE_MARKERS)


def ydl_opts(cookies_browser=None):
    opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'subtitleslangs': ['en.*'],
        'subtitlesformat': 'json3',
        'outtmpl': os.path.join(RAW_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        # Deliberately NOT ignoreerrors: a swallowed 429 is indistinguishable
        # from a video that genuinely has no caption track.
        'ignoreerrors': False,
        'retries': 2,
        'socket_timeout': 30,
    }
    if cookies_browser:
        opts['cookiesfrombrowser'] = (cookies_browser,)
    return opts


def json3_to_lines(path):
    """Convert a json3 caption file into (start_seconds, text) tuples."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    lines = []
    for ev in data.get('events') or []:
        segs = ev.get('segs')
        if not segs:
            continue
        text = ''.join(s.get('utf8', '') for s in segs)
        text = ' '.join(text.split())
        if not text:
            continue
        start = (ev.get('tStartMs') or 0) / 1000.0
        # Auto-captions emit rolling duplicates; skip immediate repeats.
        if lines and lines[-1][1] == text:
            continue
        lines.append((start, text))
    return lines


def pick_raw(video_id):
    """Prefer the original-language track when both en-orig and en exist."""
    candidates = glob.glob(os.path.join(RAW_DIR, f'{video_id}.*.json3'))
    if not candidates:
        return None
    for c in candidates:
        if '.en-orig.' in c:
            return c
    return candidates[0]


def cleanup_raw(video_id):
    for c in glob.glob(os.path.join(RAW_DIR, f'{video_id}.*')):
        try:
            os.remove(c)
        except OSError:
            pass


def write_transcript(video, lines):
    vid = video['id']
    out_path = os.path.join(OUT_DIR, f'{vid}.txt')
    # Write via a temp file so an interrupted run never leaves a partial
    # transcript that the resume check would mistake for a completed one.
    tmp_path = out_path + '.part'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(f"# {video.get('title', '')}\n")
        f.write(f"# https://www.youtube.com/watch?v={vid}\n")
        f.write(f"# duration_sec: {video.get('duration_sec')}\n\n")
        for start, text in lines:
            m, s = divmod(int(start), 60)
            h, m = divmod(m, 60)
            f.write(f'[{h:02d}:{m:02d}:{s:02d}] {text}\n')
    os.replace(tmp_path, out_path)


def fetch_one(video, opts):
    """Return (status, detail) where status is ok | throttled | empty."""
    vid = video['id']
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={vid}'])
    except Exception as exc:
        msg = f'{type(exc).__name__}: {exc}'
        cleanup_raw(vid)
        return ('throttled' if is_throttle(msg) else 'error'), msg

    raw = pick_raw(vid)
    if not raw:
        # The request itself succeeded, so this really is a video with no
        # English caption track - a Whisper job, not a retry.
        return 'empty', 'no caption track published'

    try:
        lines = json3_to_lines(raw)
    finally:
        cleanup_raw(vid)

    if not lines:
        return 'empty', 'caption track was empty'

    write_transcript(video, lines)
    return 'ok', f'{len(lines)} lines'


def seed_from_existing(videos):
    """Copy transcripts already fetched elsewhere into the output directory."""
    copied = 0
    for v in videos:
        dest = os.path.join(OUT_DIR, f"{v['id']}.txt")
        if os.path.exists(dest):
            continue
        for src_dir in SEED_DIRS:
            src = os.path.join(src_dir, f"{v['id']}.txt")
            if os.path.abspath(src) != os.path.abspath(dest) and os.path.exists(src):
                shutil.copy2(src, dest)
                copied += 1
                break
    return copied


def main():
    global _resume_at, OUT_DIR, RAW_DIR, FAIL_PATH

    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default=INDEX,
                    help='JSON file with a `videos` list; defaults to the full '
                         'channel index')
    ap.add_argument('--out-dir', default=OUT_DIR,
                    help='where transcripts and the failure list are written')
    ap.add_argument('--no-seed', action='store_true',
                    help='do not reuse transcripts already fetched elsewhere')
    ap.add_argument('--limit', type=int, default=None,
                    help='only attempt the first N outstanding videos')
    ap.add_argument('--workers', type=int, default=3,
                    help='parallel downloads; above ~4 YouTube starts issuing 429s')
    ap.add_argument('--sleep', type=float, default=1.0,
                    help='per-worker pause between videos, jittered')
    ap.add_argument('--cookies-from-browser', default=None,
                    help='browser to lift YouTube cookies from (chrome, firefox, '
                         'edge). Signed-in requests are throttled far less.')
    ap.add_argument('--backoff', type=float, default=90.0,
                    help='seconds every worker pauses after a rate limit')
    args = ap.parse_args()

    OUT_DIR = args.out_dir
    FAIL_PATH = os.path.join(OUT_DIR, '_failures.json')

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    with open(args.index, encoding='utf-8') as f:
        videos = json.load(f)['videos']

    if not args.no_seed:
        seeded = seed_from_existing(videos)
        if seeded:
            print(f'Reused {seeded} transcripts already fetched locally',
                  flush=True)

    failures = {}
    if os.path.exists(FAIL_PATH):
        with open(FAIL_PATH, encoding='utf-8') as f:
            failures = json.load(f)

    todo = [v for v in videos
            if not os.path.exists(os.path.join(OUT_DIR, f"{v['id']}.txt"))
            and v['id'] not in failures]
    # Counted before --limit truncates the queue, so the figure reports real
    # progress against the index rather than progress against this run.
    have = len(videos) - len(todo) - len(failures)
    if args.limit:
        todo = todo[:args.limit]
    print(f'Index: {len(videos)} videos | have {have} | '
          f'permanent failures {len(failures)} | to fetch {len(todo)} | '
          f'workers {args.workers}'
          f"{' | cookies: ' + args.cookies_from_browser if args.cookies_from_browser else ''}",
          flush=True)

    opts = ydl_opts(args.cookies_from_browser)
    counts = {'done': 0, 'ok': 0, 'empty': 0, 'error': 0, 'throttled': 0}
    started = time.time()

    def work(v):
        global _resume_at
        # Honour a backoff window opened by whichever worker hit the 429.
        while True:
            with _lock:
                wait = _resume_at - time.time()
            if wait <= 0:
                break
            time.sleep(min(wait, 5.0))

        status, detail = fetch_one(v, opts)

        if status == 'throttled':
            with _lock:
                _resume_at = max(_resume_at, time.time() + args.backoff)
        else:
            time.sleep(args.sleep * random.uniform(0.5, 1.5))
        return v, status, detail

    pending = list(todo)
    round_no = 0

    # Throttled videos are retried in later rounds rather than abandoned.
    while pending and round_no < 6:
        round_no += 1
        retry = []
        if round_no > 1:
            print(f'--- retry round {round_no}: {len(pending)} throttled videos, '
                  f'pausing {args.backoff:.0f}s first', flush=True)
            time.sleep(args.backoff)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(work, v) for v in pending]
            for fut in as_completed(futures):
                v, status, detail = fut.result()
                with _lock:
                    counts['done'] += 1
                    counts[status] = counts.get(status, 0) + 1

                    if status == 'throttled':
                        retry.append(v)
                    elif status in ('empty', 'error'):
                        failures[v['id']] = detail
                        with open(FAIL_PATH, 'w', encoding='utf-8') as f:
                            json.dump(failures, f, indent=2)

                    if counts['done'] % 25 == 0 or status == 'error':
                        elapsed = max(time.time() - started, 1e-9)
                        rate = counts['ok'] / elapsed * 60
                        left = len(todo) - counts['ok']
                        eta = left / rate if rate > 0 else 0
                        print(f"[{counts['ok']}/{len(todo)}] {v['id']} {status} | "
                              f"empty={counts['empty']} err={counts['error']} "
                              f"throttled={counts['throttled']} | "
                              f'{rate:.0f}/min | ~{eta:.0f} min left', flush=True)

        pending = retry
        if pending:
            counts['throttled'] = 0

    if pending:
        print(f'Still throttled after {round_no} rounds: {len(pending)} videos. '
              'Re-run later, ideally with --cookies-from-browser.', flush=True)

    print(f"Done. ok={counts['ok']} | no-captions={counts['empty']} | "
          f"errors={counts['error']} | permanent failures on file={len(failures)}",
          flush=True)


if __name__ == '__main__':
    main()

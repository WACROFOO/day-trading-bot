#!/usr/bin/env python3
"""Build a metadata index of a YouTube channel's videos.

Metadata only: video id, title, duration, view count, approximate upload date.
No video or transcript content is downloaded. Output is a JSON index used as a
research catalogue for the knowledge base.

Usage:
    python scripts/scrape_youtube_index.py [channel_url] [output_path]
"""

import json
import os
import sys

import yt_dlp

DEFAULT_CHANNEL = 'https://www.youtube.com/@DaytradeWarrior/videos'
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), '..',
                           'knowledge-base', 'data', 'daytradewarrior_videos.json')

OPTS = {
    'extract_flat': True,
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    # Ask the tab extractor for approximate upload dates; flat mode omits exact ones.
    'extractor_args': {'youtubetab': {'approximate_date': ['']}},
}


def scrape(channel_url):
    with yt_dlp.YoutubeDL(OPTS) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get('entries') or []
    # A channel URL can yield nested playlist tabs; flatten one level if needed.
    if entries and entries[0].get('_type') == 'playlist':
        flat = []
        for e in entries:
            flat.extend(e.get('entries') or [])
        entries = flat

    videos = []
    for e in entries:
        if not e or not e.get('id'):
            continue
        videos.append({
            'id': e.get('id'),
            'title': e.get('title'),
            'url': f'https://www.youtube.com/watch?v={e.get("id")}',
            'duration_sec': e.get('duration'),
            'view_count': e.get('view_count'),
            'upload_date': e.get('upload_date'),
            'timestamp': e.get('timestamp'),
        })
    return info, videos


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CHANNEL
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    print(f'Scraping index: {channel}')
    info, videos = scrape(channel)
    print(f'  Found {len(videos)} videos')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload = {
        'channel': info.get('channel') or info.get('uploader'),
        'channel_id': info.get('channel_id'),
        'channel_url': channel,
        'video_count': len(videos),
        'videos': videos,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f'  Wrote {out_path}')


if __name__ == '__main__':
    main()

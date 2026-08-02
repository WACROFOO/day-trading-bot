# scripts/ — corpus tooling

Everything that builds and queries the knowledge base. Nothing here touches
market data or the trading engine.

| Script | What |
|---|---|
| `scrape_youtube_index.py` | Channel index → `knowledge-base/data/daytradewarrior_videos.json` (note: `/videos` tab only — live streams were a separate scrape, see `knowledge-base/streams/README.md`) |
| `fetch_subtitles.py` | Captions for a list of video ids (yt-dlp) |
| `summarize_video_index.py` | Transcript → per-video summary markdown |
| `search.py` | The main query tool: BM25 over claims and raw caption chunks, deep links with timestamps |
| `mine_streams.py` | Topic-mines the live-stream transcripts; each topic tied to an open question in the research |
| `run_scanner.py` | CLI wrapper for the paper-trading platform's scanner |
| `pipeline/` | The numbered corpus pipeline — see its README |

# scripts/pipeline/ — the corpus build, in order

Numbered stages; each consumes the previous one's output. Run what changed,
not the whole chain.

| Stage | What |
|---|---|
| `00_select_teaching.py` | Choose the teaching shortlist from the channel index (this filter is why daily recaps and live streams needed separate scrapes) |
| `01_chunk.py` | Transcripts → retrievable caption chunks |
| `02_embed.py` | Optional dense vectors (needs numpy + sentence-transformers; BM25 works without it) |
| `03_cluster.py` | Group chunks by topic |
| `04_plan_summaries.py` | Plan the per-video summaries |
| `06_build_index.py` | Build the search index |
| `07_extract_rules.py` | Summaries → ranked rules digest + parameter distributions (`knowledge-base/data/rules_digest.md`); also the taxonomy other stages import |
| `08_define_support.py` | What "support" means, from 1,834 usages |
| `09_level_mechanics.py` | Level mechanics extract |
| `10_define_discretionary.py` | The discretionary vocabulary, defined |
| `11_platform_features.py` | Platform/hotkey features extract |
| `12_build_claims_db.py` | Summaries + chunks → `data/claims.db` (what `search.py` queries) |
| `13_render_v2_docs.py` | Claims DB → `PLAYBOOK_V2.md` / `STRATEGY_V2.md` (GENERATED — edit the `STEPS` list here, never the output files) |

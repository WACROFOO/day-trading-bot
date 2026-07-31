#!/usr/bin/env python3
"""Embed every chunk into a vector so near-identical explanations collapse.

Runs a local sentence-transformer, so there is no API cost and the corpus never
leaves the machine. Vectors are L2-normalised, which makes cosine similarity a
plain dot product for the clustering and search stages.

Input:  data/kb/chunks.jsonl
Output: data/kb/embeddings.npy   float32, one row per chunk, same order as input
        data/kb/embed_meta.json  model name, dimensions, row count

Usage:
    python scripts/pipeline/02_embed.py [--model NAME] [--batch 64]
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
KB_DIR = os.path.join(ROOT, 'data', 'kb')
CHUNKS = os.path.join(KB_DIR, 'chunks.jsonl')
EMB_PATH = os.path.join(KB_DIR, 'embeddings.npy')
META_PATH = os.path.join(KB_DIR, 'embed_meta.json')

DEFAULT_MODEL = 'BAAI/bge-small-en-v1.5'


def load_texts(path):
    texts = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            texts.append(json.loads(line)['text'])
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--batch', type=int, default=64)
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer

    texts = load_texts(CHUNKS)
    print(f'Chunks: {len(texts):,}', flush=True)

    print(f'Loading {args.model} (first run downloads the weights)...', flush=True)
    model = SentenceTransformer(args.model)
    dim = model.get_sentence_embedding_dimension()

    out = np.zeros((len(texts), dim), dtype=np.float32)
    started = time.time()
    step = args.batch * 40

    for i in range(0, len(texts), step):
        block = texts[i:i + step]
        out[i:i + len(block)] = model.encode(
            block,
            batch_size=args.batch,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        done = i + len(block)
        rate = done / max(time.time() - started, 1e-9)
        left = (len(texts) - done) / max(rate, 1e-9) / 60
        print(f'  {done:,}/{len(texts):,}  {rate:.0f}/s  ~{left:.1f} min left',
              flush=True)

    np.save(EMB_PATH, out)
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump({'model': args.model, 'dim': dim, 'rows': len(texts)}, f, indent=2)

    print(f'Wrote {out.shape} -> {EMB_PATH}', flush=True)


if __name__ == '__main__':
    main()

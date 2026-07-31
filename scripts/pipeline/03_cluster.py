#!/usr/bin/env python3
"""Group near-identical explanations so each idea is extracted once.

The channel repeats the same lessons for a decade. Clustering the chunk vectors
turns that redundancy from a cost into a signal: how many distinct videos a
cluster spans is a direct measure of how central the idea is to his method.

Each cluster is reduced to the members closest to its centre, which become the
evidence passed to the extraction stage.

Input:  data/kb/chunks.jsonl, data/kb/embeddings.npy
Output: data/kb/clusters.json

Usage:
    python scripts/pipeline/03_cluster.py [--k N] [--members 8]
"""

import argparse
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
KB_DIR = os.path.join(ROOT, 'data', 'kb')
CHUNKS = os.path.join(KB_DIR, 'chunks.jsonl')
EMB_PATH = os.path.join(KB_DIR, 'embeddings.npy')
OUT_PATH = os.path.join(KB_DIR, 'clusters.json')


def load_chunks(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--k', type=int, default=None,
                    help='number of clusters (default: chunks/20)')
    ap.add_argument('--members', type=int, default=8,
                    help='representative members kept per cluster')
    args = ap.parse_args()

    from sklearn.cluster import MiniBatchKMeans

    chunks = load_chunks(CHUNKS)
    emb = np.load(EMB_PATH)
    if len(chunks) != emb.shape[0]:
        sys.exit(f'Mismatch: {len(chunks)} chunks vs {emb.shape[0]} vectors. '
                 'Re-run 02_embed.py.')

    k = args.k or max(200, len(chunks) // 20)
    print(f'Clustering {len(chunks):,} chunks into {k:,} groups...', flush=True)

    km = MiniBatchKMeans(n_clusters=k, batch_size=4096, n_init=3,
                         max_iter=200, random_state=0)
    labels = km.fit_predict(emb)

    # Vectors are normalised, so a dot product against the centroid ranks
    # members by cosine similarity to the centre of the idea.
    centroids = km.cluster_centers_
    sims = np.einsum('ij,ij->i', emb, centroids[labels])

    order = np.argsort(labels, kind='stable')
    clusters = []
    start = 0
    while start < len(order):
        label = labels[order[start]]
        end = start
        while end < len(order) and labels[order[end]] == label:
            end += 1

        idx = order[start:end]
        idx = idx[np.argsort(-sims[idx])]           # most central first
        videos = {chunks[i]['video_id'] for i in idx}

        clusters.append({
            'cluster_id': int(label),
            'size': int(len(idx)),
            'n_videos': len(videos),
            'members': [{
                'chunk_id': chunks[i]['chunk_id'],
                'video_id': chunks[i]['video_id'],
                'title': chunks[i]['title'],
                'url': chunks[i]['url'],
                't_start': chunks[i]['t_start'],
                'similarity': round(float(sims[i]), 4),
                'text': chunks[i]['text'],
            } for i in idx[:args.members]],
        })
        start = end

    # Spanning many videos means the idea recurs across years, not just within
    # one long recording; that is the stronger signal of a core rule.
    clusters.sort(key=lambda c: (-c['n_videos'], -c['size']))

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'n_chunks': len(chunks), 'k': k, 'clusters': clusters},
                  f, ensure_ascii=False, indent=1)

    sizes = np.array([c['size'] for c in clusters])
    print(f'Clusters: {len(clusters):,} | median size {np.median(sizes):.0f} | '
          f'max {sizes.max()}', flush=True)
    print('Top 10 by video spread:', flush=True)
    for c in clusters[:10]:
        snippet = ' '.join(c['members'][0]['text'].split()[:16])
        print(f"  {c['n_videos']:>4} vids / {c['size']:>4} chunks  {snippet}...",
              flush=True)
    print(f'Wrote {OUT_PATH}', flush=True)


if __name__ == '__main__':
    main()

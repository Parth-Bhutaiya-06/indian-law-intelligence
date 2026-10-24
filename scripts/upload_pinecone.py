#!/usr/bin/env python
"""Embed chunks.jsonl with the LOCAL model and upsert to Pinecone.
   python scripts/upload_pinecone.py            # embed (cached) + upload
   python scripts/upload_pinecone.py --dry-run  # embed only, no Pinecone
   python scripts/upload_pinecone.py --reset    # wipe the namespace first"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from legal_rag import config, embedder, store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--batch-size", type=int, default=32)
    a = ap.parse_args()

    recs = [json.loads(l) for l in open(config.CHUNKS_PATH, encoding="utf-8")]
    ids = [r["id"] for r in recs]
    if config.EMB_PATH.exists() and config.EMB_IDS_PATH.exists() and json.load(open(config.EMB_IDS_PATH)) == ids \
            and np.load(config.EMB_PATH).shape == (len(ids), config.EMBED_DIM):
        vecs = np.load(config.EMB_PATH)
        print(f"Reusing cached embeddings {vecs.shape}")
    else:
        print(f"Embedding {len(recs)} chunks with {config.EMBED_MODEL} ...")
        vecs = embedder.embed_documents([r["embed_text"] for r in recs], batch_size=a.batch_size)
        np.save(config.EMB_PATH, vecs)
        json.dump(ids, open(config.EMB_IDS_PATH, "w"))
    if a.dry_run:
        print("dry run done", vecs.shape)
        return
    index = store.ensure_index()
    if a.reset:
        index.delete(delete_all=True, namespace=config.PINECONE_NAMESPACE)
    store.upsert(index, ids, vecs, [r["metadata"] for r in recs])
    print(index.describe_index_stats())


if __name__ == "__main__":
    main()

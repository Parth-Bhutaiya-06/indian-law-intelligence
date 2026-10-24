"""Pinecone helpers: create index, batched idempotent upsert, filtered query."""
from __future__ import annotations

import time

from . import config


def _client():
    from pinecone import Pinecone

    if not config.PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY missing (put it in .env)")
    return Pinecone(api_key=config.PINECONE_API_KEY)


def ensure_index():
    from pinecone import ServerlessSpec

    pc = _client()
    if not pc.has_index(config.PINECONE_INDEX):
        pc.create_index(
            name=config.PINECONE_INDEX, dimension=config.EMBED_DIM, metric=config.PINECONE_METRIC,
            spec=ServerlessSpec(cloud=config.PINECONE_CLOUD, region=config.PINECONE_REGION),
        )
        while not pc.describe_index(config.PINECONE_INDEX).status["ready"]:
            time.sleep(2)
    else:
        dim = pc.describe_index(config.PINECONE_INDEX).dimension
        if dim != config.EMBED_DIM:
            raise RuntimeError(f"Index '{config.PINECONE_INDEX}' has dimension {dim}, but the embedding model gives {config.EMBED_DIM}.")
    return pc.Index(config.PINECONE_INDEX)


def get_index():
    return _client().Index(config.PINECONE_INDEX)


def upsert(index, ids, vectors, metadatas, batch_size: int = 100):
    from tqdm import tqdm

    for i in tqdm(range(0, len(ids), batch_size), desc="upsert"):
        batch = [{"id": ids[j], "values": vectors[j].tolist(), "metadata": metadatas[j]} for j in range(i, min(i + batch_size, len(ids)))]
        for attempt in range(5):
            try:
                index.upsert(vectors=batch, namespace=config.PINECONE_NAMESPACE)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)


def query(index, vector, top_k=8, flt=None):
    res = index.query(vector=vector, top_k=top_k, include_metadata=True, filter=flt, namespace=config.PINECONE_NAMESPACE)
    return res["matches"]

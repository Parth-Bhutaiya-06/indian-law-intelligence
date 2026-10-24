"""Local sentence-embedding model (no API). Vectors are L2-normalised -> use cosine/dot in Pinecone."""
from __future__ import annotations

import numpy as np

from . import config

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        import torch

        device = "cuda" if torch.cuda.is_available() else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
        _model = SentenceTransformer(config.EMBED_MODEL, device=device)
        _model.max_seq_length = config.MODEL_MAX_TOKENS
        dim = _model.get_sentence_embedding_dimension()
        assert dim == config.EMBED_DIM, f"Model outputs {dim} dims but EMBED_DIM={config.EMBED_DIM}; fix config/Pinecone index."
    return _model


def embed_documents(texts: list[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
    texts = [config.DOC_PREFIX + t for t in texts]
    return get_model().encode(texts, batch_size=batch_size, normalize_embeddings=True,
                              show_progress_bar=show_progress, convert_to_numpy=True).astype("float32")


def embed_query(q: str) -> list[float]:
    v = get_model().encode([config.QUERY_PREFIX + q], normalize_embeddings=True, convert_to_numpy=True)[0]
    return v.astype("float32").tolist()

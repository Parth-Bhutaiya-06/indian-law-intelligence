"""Retrieval (local embeddings + Pinecone, with metadata-aware routing) and generation (Groq)."""
from __future__ import annotations

import re

from . import config, embedder, store

_SEC = r"(\d{1,3}[A-Z]{0,2})(?:\s*\(\w{1,3}\))*"
_ACTS = "|".join(sorted((a for als in config.ACT_ALIASES.values() for a in als), key=len, reverse=True))
RE_ACT_SEC = re.compile(rf"\b({_ACTS})\b[\s,:.-]*(?:section|sec\.?|s\.)?\s*{_SEC}\b", re.I)
RE_SEC_ACT = re.compile(rf"\b(?:section|sec\.?|s\.|u/s)\s*{_SEC}\s*(?:of|under|,)?\s*(?:the\s+)?({_ACTS})\b", re.I)
RE_SEC_ONLY = re.compile(rf"\b(?:section|sec\.?|u/s)\s*{_SEC}\b", re.I)
RE_ORDER = re.compile(r"\border\s+([IVXLC]+|\d+)\s*,?\s*rule\s+(\d+)", re.I)


def _act_of(alias: str) -> str | None:
    a = alias.lower()
    for act, als in config.ACT_ALIASES.items():
        if a in als:
            return act
    return None


def parse_query(q: str) -> dict:
    """Detect explicit references such as 'section 103 BNS', 'IPC 302', 'Order XXI rule 5'."""
    out = {"act": None, "section": None, "order": None}
    m = RE_ACT_SEC.search(q)
    if m:
        out["act"], out["section"] = _act_of(m.group(1)), m.group(2).upper()
    else:
        m = RE_SEC_ACT.search(q)
        if m:
            out["act"], out["section"] = _act_of(m.group(2)), m.group(1).upper()
        else:
            m = RE_SEC_ONLY.search(q)
            if m:
                out["section"] = m.group(1).upper()
    m = RE_ORDER.search(q)
    if m:
        from .textutil import roman_to_int

        o = m.group(1)
        out["act"] = "SCR"
        out["order"] = (int(o) if o.isdigit() else roman_to_int(o), int(m.group(2)))
    return out


def retrieve(query: str, top_k: int = 8, act: str | None = None, status: str | None = None, index=None) -> list[dict]:
    """Semantic search + exact-section lookup. `act`/`status` act as hard filters when given."""
    index = index or store.get_index()
    ref = parse_query(query)
    vec = embedder.embed_query(query)
    base: dict = {}
    if act or ref["act"]:
        base["act"] = {"$eq": act or ref["act"]}
    if status:
        base["status"] = {"$eq": status}

    matches: list = []
    if ref["order"]:
        f = {**base, "order_no": {"$eq": ref["order"][0]}, "rule_no": {"$eq": ref["order"][1]}}
        matches += store.query(index, vec, 4, f)
    elif ref["section"]:
        f = {**base, "section_no": {"$eq": ref["section"]}}
        matches += store.query(index, vec, 6, f)   # exact section hits first (all acts if no act named)
        if ref["act"] in (None, "BNS"):  # BNSS First Schedule: cognizable / bailable / triable-by for that BNS section
            matches += store.query(index, vec, 2, {"act": {"$eq": "BNSS"}, "chunk_type": {"$eq": "schedule_row"}, "section_no": {"$eq": ref["section"]}})
    matches += store.query(index, vec, top_k, base or None)  # plain semantic search

    seen, out = set(), []
    for m in matches:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        out.append({"id": m["id"], "score": m["score"], **m["metadata"]})
    return out[: top_k + 4]


SYSTEM = """You are a careful legal research assistant for Indian criminal law and court procedure.
Answer ONLY from the CONTEXT passages. If the context does not contain the answer, say so plainly.
Rules:
- Cite every claim like (BNS s.103) or (BNSS s.35(1)) or (SCR Order XXI r.5), using the passage labels.
- The IPC, CrPC and Evidence Act were replaced on 1 July 2024 by the BNS, BNSS and BSA. Prefer in-force sources
  (status=in_force). If you cite an old IPC/CrPC provision, say it is repealed and give the equivalent section when the passage states it.
- Quote punishments exactly as written. Do not invent section numbers or case law.
- Supreme Court Rules text is OCR-scanned and may contain typos; flag uncertainty.
- End with one line: 'General information, not legal advice.'"""


def build_context(hits: list[dict], max_chars: int = 9000) -> str:
    parts, used = [], 0
    for i, h in enumerate(hits, 1):
        tag = f"[{i}] {h.get('label')} | {h.get('section_title', '')} | status={h.get('status')} | type={h.get('chunk_type')}"
        if h.get("equivalent_section"):
            tag += f" | equivalent {h['equivalent_act']} {h['equivalent_section']}"
        if h.get("equivalent_sections"):
            tag += f" | replaces {h['equivalent_act']} {', '.join(h['equivalent_sections'])}"
        block = f"{tag}\n{h['text']}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def answer(question: str, top_k: int = 8, act: str | None = None, status: str | None = None, temperature: float = 0.1):
    from groq import Groq

    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY missing (put it in .env)")
    hits = retrieve(question, top_k, act, status)
    ctx = build_context(hits)
    resp = Groq(api_key=config.GROQ_API_KEY).chat.completions.create(
        model=config.GROQ_MODEL, temperature=temperature, max_tokens=1200,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": f"CONTEXT:\n{ctx}\n\nQUESTION: {question}"}],
    )
    return resp.choices[0].message.content, hits

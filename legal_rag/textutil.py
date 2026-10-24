"""Text cleaning, token counting and the generic legal-aware splitter."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Callable

from . import config

# --------------------------------------------------------------------------- tokens
@lru_cache(maxsize=1)
def _hf_tokenizer():
    try:  # use the real tokenizer of the embedding model when available (exact counts)
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(config.EMBED_MODEL)
    except Exception:
        return None


_TOK_RE = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    tok = _hf_tokenizer()
    if tok is not None:
        return len(tok.encode(text, add_special_tokens=False))
    return int(len(_TOK_RE.findall(text)) * 1.15)  # WordPiece approximation


# --------------------------------------------------------------------------- cleaning
_ws = re.compile(r"[ \t ]+")


def clean_line(s: str) -> str:
    s = s.replace("\x0c", " ").replace("​", "")
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return _ws.sub(" ", s).strip()


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(r: str) -> int | None:
    r = r.upper()
    if not r or any(c not in ROMAN for c in r):
        return None
    total = 0
    for i, c in enumerate(r):
        v = ROMAN[c]
        total += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
    return total


# --------------------------------------------------------------------------- paragraphs
PARA_START = re.compile(
    r"^(\(\w{1,5}\)|Illustrations?\b|Explanations?\b|Exceptions?\b|Provided\b|Secondly|Thirdly|"
    r"Fourthly|Fifthly|Sixthly|STATE AMENDMENT|First\b\.?|Second\b\.?|—)",
)


def to_paragraphs(lines: list[str]) -> list[str]:
    """Un-wrap hard-wrapped lines into logical paragraphs (sub-sections, clauses, illustrations)."""
    paras: list[str] = []
    cur = ""
    for raw in lines:
        ln = clean_line(raw)
        if not ln:
            continue
        if cur and (PARA_START.match(ln) or cur.endswith((":—", ":-"))):
            paras.append(cur)
            cur = ln
        else:
            cur = f"{cur} {ln}".strip()
    if cur:
        paras.append(cur)
    return paras


# --------------------------------------------------------------------------- splitting
_SENT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"])")


def _split_long(unit: str, max_tokens: int) -> list[str]:
    if count_tokens(unit) <= max_tokens:
        return [unit]
    out, buf = [], ""
    for sent in _SENT.split(unit):
        cand = f"{buf} {sent}".strip()
        if buf and count_tokens(cand) > max_tokens:
            out.append(buf)
            buf = sent
        else:
            buf = cand
        if count_tokens(buf) > max_tokens:  # a single huge sentence: cut by words
            words, piece = buf.split(), []
            buf = ""
            for w in words:
                piece.append(w)
                if count_tokens(" ".join(piece)) > max_tokens:
                    out.append(" ".join(piece[:-1]))
                    piece = [w]
            buf = " ".join(piece)
    if buf:
        out.append(buf)
    return out


def pack_units(
    units: list[str],
    max_tokens: int = config.MAX_CHUNK_TOKENS,
    overlap_tokens: int = config.OVERLAP_TOKENS,
    min_tokens: int = config.MIN_CHUNK_TOKENS,
    counter: Callable[[str], int] = count_tokens,
) -> list[str]:
    """Greedily pack paragraphs into chunks <= max_tokens, never cutting a paragraph unless it is
    itself too long (then by sentence). A short last unit is repeated at the start of the next chunk."""
    flat: list[str] = []
    for u in units:
        flat.extend(_split_long(u, max_tokens))
    chunks: list[list[str]] = []
    cur: list[str] = []
    cur_t = 0
    for u in flat:
        t = counter(u)
        if cur and cur_t + t > max_tokens:
            chunks.append(cur)
            tail = cur[-1]
            cur = [tail] if counter(tail) <= overlap_tokens and len(cur) > 1 else []
            cur_t = counter(tail) if cur else 0
        cur.append(u)
        cur_t += t
    if cur:
        chunks.append(cur)
    # merge a tiny tail chunk into its predecessor
    if len(chunks) > 1 and sum(counter(u) for u in chunks[-1]) < min_tokens:
        tail = chunks.pop()
        chunks[-1].extend(u for u in tail if u not in chunks[-1][-1:])
    return [" ".join(c) for c in chunks]

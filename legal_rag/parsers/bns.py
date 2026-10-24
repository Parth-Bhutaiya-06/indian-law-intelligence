"""Parser for 'The Bharatiya Nyaya Sanhita, 2023 [As on 6th Oct 2025]' (India Code text).

Section format:  `103. Punishment for murder.—(1) Whoever ...`  (title may wrap onto the next line).
Page numbers are bare-digit lines at the TOP of a page; footnotes are `1. Subs. by ...` at the bottom."""
from __future__ import annotations

import re
from pathlib import Path

from ..textutil import clean_line
from .common import CHAPTER_RE, Provision, is_heading_line
from .engine import run_engine

START = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.[\s—–]*\S")
HEAD = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.[\s—–]*(.+?)\.?\s*[—–]+\s*(.*)$")
FOOTNOTE_WORDS = re.compile(
    r"^\d{1,2}\.\s+(Ins\.|Subs\.|Omitted|Added|The words|Clause|Sub-section|\d{1,2}(st|nd|rd|th) day|Came into force|Vide|See )|vide notification|w\.e\.f\.",
    re.I,
)


def _heading(i, lines):
    ln = lines[i]
    if not START.match(ln) or FOOTNOTE_WORDS.search(ln):
        return None
    joined, used = ln, 1
    m = HEAD.match(joined)
    while not m and used < 3 and i + used < len(lines):
        joined += " " + lines[i + used]
        used += 1
        m = HEAD.match(joined)
    if not m:
        return None
    num, suf, title, rest = m.groups()
    if len(title) > 220:
        return None
    return int(num), suf, title, rest, used


def _chapter(i, lines):
    m = re.match(r"^CHAPTER\s+([IVXLC]+)\s*$", lines[i])
    if not m:
        return None
    title, used = [], 1
    while i + used < len(lines) and used <= 2 and is_heading_line(lines[i + used]) and not lines[i + used].startswith("CHAPTER"):
        title.append(lines[i + used])
        used += 1
    return m.group(1), " ".join(title), used


def parse(path: Path) -> tuple[list[Provision], dict]:
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(i for i, l in enumerate(raw) if l.startswith("BE it enacted"))
    lines, pages, page = [], [], None
    skipping_footnote = False
    for r in raw[start + 1:]:
        ln = clean_line(r)
        if not ln:
            skipping_footnote = False if skipping_footnote and False else skipping_footnote
            continue
        if re.fullmatch(r"\d{1,3}", ln):          # page number at top of page
            page = int(ln)
            skipping_footnote = False
            continue
        lines.append(ln)
        pages.append(page)
    provs, info = run_engine(lines, pages, "bns", _heading, _chapter, max_gap=3)
    # strip footnotes (numbered lines like "1. 1st day of July..." + wrapped continuation) from provisions
    for p in provs:
        kept, skip = [], False
        for ln in p.lines:
            if re.match(r"^\d{1,2}\.\s", ln) and FOOTNOTE_WORDS.search(ln):
                skip = True
                continue
            if skip and (re.match(r"^\(\w{1,5}\)|^Explanation|^Illustration|^Provided|^[A-Z]{1}\b", ln) and not re.match(r"^\d", ln)):
                # footnote continuations are plain wrapped text; real clauses start with (x)/Explanation/...
                skip = False
            if skip:
                continue
            kept.append(ln)
        p.lines = kept
    return provs, info

"""Parser for the BSA 2023 gazette PDF. Uses word x-positions to split the left margin (section titles)
from the body text, so BSA sections DO get a proper `section_title`."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from ..textutil import clean_line
from .common import Provision, is_heading_line
from .engine import run_engine

BODY_X = 116.0      # body column starts here (left margin pages)
BODY_X_END = 481.0   # body column ends here (right margin pages)
START = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.\s*(?=[\(A-Za-z\"])")


def _group_lines(words, tol=3.0):
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [(r[0]["top"], clean_line(" ".join(x["text"] for x in sorted(r, key=lambda x: x["x0"])))) for r in rows]


def _page_lines(pg):
    words = [w for w in pg.extract_words() if w["top"] > 75 and w["top"] < 800]  # drop running header
    body = _group_lines([w for w in words if BODY_X <= w["x0"] < BODY_X_END])
    margin = _group_lines([w for w in words if w["x0"] < BODY_X or w["x0"] >= BODY_X_END])
    body = [(t, s) for t, s in body if s and "____" not in s]
    return body, [(t, s) for t, s in margin if s and "____" not in s]


def parse(path: Path) -> tuple[list[Provision], dict]:
    lines, pages, tops, margins = [], [], [], {}
    with pdfplumber.open(str(path)) as pdf:
        for pno, pg in enumerate(pdf.pages, start=1):
            if pno == 1:  # cover page has a different layout: body starts after "BE it enacted"
                text = pg.extract_text() or ""
                txt = text.split("follows:—", 1)[-1]
                for ln in txt.splitlines():
                    ln = clean_line(ln)
                    if ln:
                        lines.append(ln); pages.append(pno); tops.append(0.0)
                continue
            body, margin = _page_lines(pg)
            margins[pno] = margin
            for t, s in body:
                lines.append(s); pages.append(pno); tops.append(t)

    def heading(i, ls):
        m = START.match(ls[i])
        if not m:
            return None
        return int(m.group(1)), m.group(2), "", ls[i][m.end():], 1

    def chapter(i, ls):
        m = re.match(r"^CHAPTER\s+([IVXLC]+)\s*$", ls[i])
        if not m:
            return None
        used, title = 1, []
        while i + used < len(ls) and used <= 3 and is_heading_line(ls[i + used]) and not ls[i + used].startswith(("PART", "CHAPTER")):
            title.append(ls[i + used]); used += 1
        return m.group(1), " ".join(title), used

    def part(i, ls):
        m = re.match(r"^PART\s+([IVX]+)\s*$", ls[i])
        return (f"Part {m.group(1)}", 1) if m else None

    # remember (page, top) of each provision start to attach margin titles afterwards
    provs, info = run_engine(lines, pages, "bsa", heading, chapter, part, max_gap=3)
    starts = {}
    keyed = []
    for i, ln in enumerate(lines):
        m = START.match(ln)
        if m:
            keyed.append((i, m.group(1) + m.group(2)))
    pos = {}
    for i, k in keyed:
        pos.setdefault(k, []).append(i)
    for idx, p in enumerate(provs):
        cands = pos.get(p.section_no, [])
        if not cands:
            continue
        i = next((c for c in cands if pages[c] == p.page), cands[0])
        pg, top = pages[i], tops[i]
        nxt = min([tops[j] for j in range(i + 1, len(lines)) if pages[j] == pg and START.match(lines[j]) and tops[j] > top + 1] or [9999])
        title_parts = [s for t, s in margins.get(pg, []) if top - 4 <= t < min(top + 60, nxt - 3)]
        p.title = " ".join(title_parts).strip()
    if provs and not provs[0].title:
        provs[0].title = "Short title, application and commencement"
    return provs, info

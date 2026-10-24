"""Parser for the annotated Indian Penal Code text (statute + case-law commentary).

Heading format:  `300. Murder —` (title may wrap over 1-3 lines, ends with an em dash)."""
from __future__ import annotations

import re
from pathlib import Path

from ..textutil import clean_line
from .common import Provision
from .engine import run_engine

START = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.\s+\S")
REPEALED = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.\s+(Repealed|Omitted)\b", re.I)


DASH = re.compile(r"\s[—–-]\s*(?=$|\s)|—")
RANGE = re.compile(r"^(\d{1,3})\s+To\s+(\d{1,3}[A-Z]?)\s*[—–-]?", re.I)


def _heading(i, lines):
    ln = lines[i]
    m = REPEALED.match(ln)
    if m:
        return int(m.group(1)), m.group(2), m.group(3).title(), "", 1
    m = RANGE.match(ln)
    if m:
        return int(m.group(1)), "", f"Repealed (sections {m.group(1)} to {m.group(2)})", "", 1
    if not START.match(ln):
        return None
    joined, used = ln, 1
    # collect heading lines up to the first blank line (max 5)
    while used < 5 and i + used < len(lines) and lines[i + used] and not DASH.search(joined):
        joined += " " + lines[i + used]
        used += 1
    d = DASH.search(joined)
    if d:
        head, rest = joined[: d.start()], joined[d.end():]
    else:  # heading with no dash: ends at the blank line
        head, rest = joined, ""
    m = re.match(r"^(\d{1,3})([A-Z]{0,2})\.\s+(.+)$", head.strip())
    if not m or len(m.group(3)) > 260:
        return None
    return int(m.group(1)), m.group(2), m.group(3).strip().rstrip(".—–- "), rest.strip(), used


def _chapter(i, lines):
    m = re.match(r"^CHAPTER\s+([IVXLC]+A?)\s*[-–—]\s*(.+)$", lines[i], re.I)
    if not m:
        return None
    title, used = m.group(2).strip(), 1
    if i + 1 < len(lines) and lines[i + 1].isupper() and not re.match(r"^\d", lines[i + 1]) and len(lines[i + 1]) < 100:
        title += " " + lines[i + 1]
        used = 2
    return m.group(1).upper(), title.upper(), used


def parse(path: Path) -> tuple[list[Provision], dict]:
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    idx = [i for i, l in enumerate(raw) if re.match(r"^CHAPTER I - INTRODUCTION", l.strip())]
    start = idx[-1]  # second occurrence = body (first is the table of contents)
    lines = [clean_line(l) for l in raw[start:]]
    provs, info = run_engine(lines, [None] * len(lines), "ipc_txt", _heading, _chapter, max_gap=6)
    return provs, info

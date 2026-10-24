"""Parser for the BNSS 2023 gazette text (sections + First Schedule + Second Schedule forms).

Gazette artefacts removed: Devanagari/garbled header lines, 'THE GAZETTE OF INDIA' running heads, page numbers.
Marginal notes (section titles) are interleaved with the text in this extraction and cannot be reliably
re-attached, so BNSS sections have no `section_title`; a `heading_hint` (first words) is added instead."""
from __future__ import annotations

import re
from pathlib import Path

from ..textutil import clean_line, to_paragraphs
from .common import CHAPTER_RE, Provision, is_heading_line
from .engine import run_engine

JUNK = re.compile(r"xxxGID|CG-DL|GAZETTE OF INDIA|_{6,}|^Sec\.\s*\d+\]|[ऀ-ॿ]")
START = re.compile(r"^(\d{1,3})([A-Z]{0,2})\.\s+(?=[\(A-Za-z\"])")


def _heading(i, lines):
    m = START.match(lines[i])
    if not m:
        return None
    return int(m.group(1)), m.group(2), "", lines[i][m.end():], 1


def _chapter(i, lines):
    m = re.match(r"^CHAPTER\s+([IVXLC]+)\s*$", lines[i])
    if not m:
        return None
    title, used = [], 1
    while i + used < len(lines) and used <= 3 and is_heading_line(lines[i + used]):
        title.append(lines[i + used])
        used += 1
    return m.group(1), " ".join(title), used


def _clean(raw: list[str]):
    lines, pages, page = [], [], None
    for r in raw:
        ln = clean_line(r)
        if not ln or JUNK.search(ln):
            continue
        if re.fullmatch(r"\d{1,3}", ln):
            page = int(ln)
            continue
        lines.append(ln)
        pages.append(page)
    return lines, pages


def parse(path: Path) -> tuple[list[Provision], dict]:
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    first = next(i for i, l in enumerate(raw) if l.strip() == "THE FIRST SCHEDULE")
    second = next(i for i, l in enumerate(raw) if l.strip() == "THE SECOND SCHEDULE")
    ch1 = next(i for i, l in enumerate(raw) if l.strip() == "CHAPTER I")
    lines, pages = _clean(raw[ch1:first])
    provs, info = run_engine(lines, pages, "bnss", _heading, _chapter, max_gap=3)
    for p in provs:
        words = " ".join(p.lines[:2]).split()
        p.extra["heading_hint"] = " ".join(words[:14])
    provs += _first_schedule(raw[first:second])
    provs += _second_schedule(raw[second:])
    info["first_schedule_rows"] = sum(1 for p in provs if p.kind == "schedule_row")
    info["forms"] = sum(1 for p in provs if p.kind == "form")
    return provs, info


# ----------------------------------------------------------------------------- First Schedule
ROW = re.compile(r"^(\d{1,3})(\s?\(\w{1,3}\))?\s+(?=[A-Z(\"])")


def _flags(text: str) -> dict:
    t = text.lower()
    out = {}
    if "non-cognizable" in t and re.search(r"(?<!non-)cognizable", t.replace("non-cognizable", "")) is None:
        out["cognizable"] = "no"
    elif "non-cognizable" not in t and "cognizable" in t and "according as" not in t:
        out["cognizable"] = "yes"
    elif "according as" in t:
        out["cognizable"] = "depends"
    if "non-bailable" in t and not re.search(r"(?<!non-)bailable", t.replace("non-bailable", "")):
        out["bailable"] = "no"
    elif "non-bailable" not in t and "bailable" in t:
        out["bailable"] = "yes"
    elif "according as" in t:
        out["bailable"] = "depends"
    return out


def _first_schedule(raw: list[str]) -> list[Provision]:
    lines, pages = _clean(raw)
    part2 = next((i for i, l in enumerate(lines) if re.match(r"^II\.\s*[—–-]", l)), len(lines))
    start = next((i for i, l in enumerate(lines) if re.match(r"^I\.\s*[—–-]", l)), 0)
    rows: list[Provision] = []
    cur, last = None, 0
    for ln, pg in zip(lines[start + 1:part2], pages[start + 1:part2]):
        if re.match(r"^(Section Offence|12 3 4 5 6|cognizable|bailable|triable)", ln, re.I):
            continue
        m = ROW.match(ln)
        if m and last <= int(m.group(1)) <= max(last + 40, 60) and len(ln.split()) >= 3:
            last = int(m.group(1))
            sec = m.group(1) + (m.group(2) or "").replace(" ", "")
            cur = Provision(doc_id="bnss", section_no=f"sch1-{sec}", title="", kind="schedule_row", page=pg,
                            part="First Schedule - Classification of offences (Part I: offences under BNS)",
                            extra={"bns_section": sec})
            cur.lines.append(ln[m.end():])
            rows.append(cur)
        elif cur is not None:
            cur.lines.append(ln)
    # Part II: offences against other laws - kept as paragraph blocks
    block = Provision(doc_id="bnss", section_no="sch1-part2", kind="schedule_row", page=None,
                      part="First Schedule - Classification of offences (Part II: offences against other laws)",
                      lines=lines[part2:])
    for r in rows:
        r.extra.update(_flags(" ".join(r.lines)))
        r.extra["heading_hint"] = " ".join(" ".join(r.lines[:2]).split()[:14])
    return rows + [block]


# ----------------------------------------------------------------------------- Second Schedule (forms)
FORM = re.compile(r"^FORM\s+No\.?\s*(\d+)", re.I)


def _second_schedule(raw: list[str]) -> list[Provision]:
    lines, pages = _clean(raw)
    forms, cur = [], None
    for ln, pg in zip(lines, pages):
        m = FORM.match(ln)
        if m:
            cur = Provision(doc_id="bnss", section_no=f"sch2-form{m.group(1)}", kind="form", page=pg,
                            part="Second Schedule - Forms", title=f"Form No. {m.group(1)}")
            forms.append(cur)
        if cur is not None:
            cur.lines.append(ln)
    for f in forms:
        refs = re.findall(r"\[See section ([\d()A-Za-z]+)", " ".join(f.lines[:6]))
        if refs:
            f.extra["form_for_section"] = refs[0]
    return forms

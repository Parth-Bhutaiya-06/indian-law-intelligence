"""Shared building blocks for the parsers: the Provision record and sequential section finding."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..textutil import roman_to_int


@dataclass
class Provision:
    """One legal provision (section / rule / schedule row) before it is chunked."""

    doc_id: str
    section_no: str                    # "103", "304B", "" for non-numbered
    title: str = ""
    lines: list[str] = field(default_factory=list)   # body lines (hard-wrapped, cleaned)
    chapter_no: str = ""               # roman numeral as printed
    chapter_title: str = ""
    part: str = ""
    page: int | None = None
    kind: str = "section"              # section | schedule_row | form | rule | preamble | ...
    extra: dict = field(default_factory=dict)  # parser specific metadata, merged into chunk metadata


def sec_key(num: int, suf: str) -> tuple[int, str]:
    return (num, suf)


def accept_next(cur: tuple[int, str] | None, num: int, suf: str, max_gap: int) -> bool:
    """Sequential-number test: accept N, N+1.., or the same number with a later letter suffix (3A after 3).
    This is what keeps footnotes ("1. 1st day of July...") and list items from being read as sections."""
    if cur is None:
        return num <= max_gap
    cn, cs = cur
    if num == cn:
        return bool(suf) and suf > cs
    return cn < num <= cn + max_gap


CHAPTER_RE = re.compile(r"^CHAPTER\s+([IVXLC]+[A-Z]?)\b\s*(?:[-–—:]\s*(.*))?$")


def is_heading_line(s: str) -> bool:
    """Chapter-title style line: mostly upper-case letters, no leading number."""
    s = s.strip()
    return bool(s) and not re.match(r"^\(?\d", s) and sum(c.isupper() for c in s) >= 0.7 * sum(c.isalpha() for c in s) and len(s) < 140

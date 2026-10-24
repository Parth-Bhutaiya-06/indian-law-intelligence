"""Generic line-walking engine: tracks chapter/part, starts a new Provision at each accepted heading."""
from __future__ import annotations

from typing import Callable, Optional

from .common import Provision, accept_next

# heading_fn(i, lines) -> (num, suffix, title, first_text, n_lines_consumed) | None
# chapter_fn(i, lines) -> (chapter_no, chapter_title, n_lines_consumed) | None
HeadingFn = Callable[[int, list[str]], Optional[tuple]]
ChapterFn = Callable[[int, list[str]], Optional[tuple]]


def run_engine(
    lines: list[str],
    pages: list[int | None],
    doc_id: str,
    heading_fn: HeadingFn,
    chapter_fn: ChapterFn | None = None,
    part_fn: Callable[[int, list[str]], Optional[tuple]] | None = None,
    max_gap: int = 3,
    stop_fn: Callable[[int, list[str]], bool] | None = None,
) -> tuple[list[Provision], dict]:
    provs: list[Provision] = []
    cur_prov: Provision | None = None
    cur_key = None
    chapter = ("", "")
    part = ""
    rejected = 0
    i = 0
    while i < len(lines):
        if stop_fn and stop_fn(i, lines):
            break
        if part_fn:
            p = part_fn(i, lines)
            if p:
                part, used = p
                i += used
                continue
        if chapter_fn:
            c = chapter_fn(i, lines)
            if c:
                chapter = (c[0], c[1])
                i += c[2]
                continue
        h = heading_fn(i, lines)
        if h:
            num, suf, title, first, used = h
            if accept_next(cur_key, num, suf, max_gap):
                cur_key = (num, suf)
                cur_prov = Provision(
                    doc_id=doc_id, section_no=f"{num}{suf}", title=title.strip(),
                    chapter_no=chapter[0], chapter_title=chapter[1], part=part, page=pages[i],
                )
                if first:
                    cur_prov.lines.append(first)
                provs.append(cur_prov)
                i += used
                continue
            rejected += 1
        if cur_prov is not None:
            cur_prov.lines.append(lines[i])
        i += 1
    return provs, {"rejected_headings": rejected, "last_section": cur_key}

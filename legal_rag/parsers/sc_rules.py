"""Parser for the Supreme Court Rules, 2013 (OCR text - noisy). Splits into Order -> Rule, then
schedules/forms as blocks. Rule numbers are matched strictly in sequence (with OCR digit confusions)."""
from __future__ import annotations

import re
from pathlib import Path

from ..textutil import clean_line, roman_to_int
from .common import Provision, is_heading_line

JUNK = re.compile(r"GAZ|PART II.{0,3}SEC|^\d{4}\s*G[Il1]|^\d{1,3}\s*$")
ORDER = re.compile(r"^\W{0,3}ORDER\s+([IVXLC]+)\b")
PART = re.compile(r"^\W{0,4}PART\s*[-–]?\s*([IVX]+)\s*$")
BLOCK = re.compile(r"^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH)\s+SCHEDULE\b|^APPENDIX\b|^FORM\s+(No\.?\s*)?[IVX\d]+\b", re.I)
OCR = {1: "Il|", 5: "S", 6: "G", 8: "aB", 0: "O"}


def _rule_no(line: str, expected: int) -> int | None:
    """Return the rule number if `line` starts a rule: expected, or up to 3 ahead (OCR may have lost a rule)."""
    m = re.match(r"^([A-Za-z0-9|]{1,3})\s?\.\s?(?=[\(\w\"'“])", line)
    if not m:
        return None
    tok = m.group(1)
    for n in range(expected, expected + 4):
        if tok == str(n) or (n < 10 and tok in OCR.get(n, "")):
            return n
    return None


def parse(path: Path) -> tuple[list[Provision], dict]:
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = [clean_line(r) for r in raw]
    lines = [l for l in lines if l and not JUNK.search(l)]
    start = next(i for i, l in enumerate(lines) if ORDER.match(l))
    provs: list[Provision] = []
    cur: Provision | None = None
    order_no, order_roman, order_title = 0, "", ""
    part_no, part_title = 1, "GENERAL"
    next_rule = 1
    block_mode = False
    i = start
    while i < len(lines):
        ln = lines[i]
        pm = PART.match(ln)
        if pm and (roman_to_int(pm.group(1)) or 0) == part_no + 1:
            part_no += 1
            part_title = lines[i + 1] if i + 1 < len(lines) and is_heading_line(lines[i + 1]) else ""
            if "SCHEDULE" in part_title.upper():
                block_mode = True
            i += 1
            continue
        if not block_mode:
            om = ORDER.match(ln)
            if om:
                n = roman_to_int(om.group(1)) or 0
                if order_no < n <= order_no + 6:
                    order_no, order_roman, next_rule, cur = n, om.group(1), 1, None
                    t = []
                    j = i + 1
                    while j < len(lines) and len(t) < 2 and is_heading_line(lines[j]) and not ORDER.match(lines[j]):
                        t.append(lines[j]); j += 1
                    order_title = " ".join(t)
                    i = j
                    continue
            rn = _rule_no(ln, next_rule) if order_no else None
            if rn:
                next_rule = rn
                cur = Provision(doc_id="scr", section_no=f"{order_no}.{next_rule}", kind="rule", part=f"Part {part_no} {part_title}".strip(),
                                chapter_no=order_roman, chapter_title=order_title, title="",
                                extra={"order_no": order_no, "order_roman": order_roman, "rule_no": next_rule})
                cur.lines.append(re.sub(r"^[A-Za-z0-9|]{1,3}\s?\.\s?", "", ln))
                provs.append(cur)
                next_rule += 1
                i += 1
                continue
        else:
            bm = BLOCK.match(ln)
            if bm:
                name = re.sub(r"\W+", "-", ln[:40]).strip("-").lower()
                cur = Provision(doc_id="scr", section_no=name, kind="schedule", part=f"Part {part_no} {part_title}".strip(),
                                title=ln[:80], extra={"order_no": 0})
                provs.append(cur)
        if cur is not None:
            cur.lines.append(ln)
        i += 1
        if not block_mode and cur is not None and BLOCK.match(ln) and ln.upper().startswith(("FIRST SCHEDULE",)):
            block_mode = True
    return provs, {"orders_found": order_no, "rules": sum(p.kind == "rule" for p in provs), "blocks": sum(p.kind == "schedule" for p in provs)}

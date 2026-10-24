"""Turns Provisions into retrieval-ready chunks (text + rich flat metadata, Pinecone compatible)."""
from __future__ import annotations

import re

from . import config, enrich
from .parsers.common import Provision
from .textutil import count_tokens, pack_units, to_paragraphs

ORDINAL_CLEAN = re.compile(r"\b\d{1,2} of \d{4}\.?")


def _label(act: str, p: Provision) -> str:
    if p.doc_id == "scr":
        if p.kind == "rule":
            return f"Order {p.chapter_no} Rule {p.extra.get('rule_no')}"
        return p.title or p.section_no
    if p.kind == "schedule_row":
        return f"First Schedule row for BNS section {p.extra.get('bns_section', '')}".strip() if p.extra.get("bns_section") else "First Schedule (offences against other laws)"
    if p.kind == "form":
        return f"Second Schedule {p.title}"
    return f"Section {p.section_no}"


def _units(p: Provision) -> list[str]:
    if p.kind == "schedule_row" and p.extra.get("bns_section"):
        return [" ".join(" ".join(p.lines).split())]
    return to_paragraphs(p.lines)


def _chunk_type(p: Provision, text: str) -> str:
    if p.kind != "section":
        return {"schedule_row": "schedule_row", "form": "form", "plain_language": "plain_language",
                "rule": "rule", "schedule": "schedule"}.get(p.kind, p.kind)
    if enrich.case_citations(text) >= 2:
        return "case_law_commentary"
    if re.match(r"^Illustrations?\b", text):
        return "illustrations"
    return "provision"


def _clean_meta(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, list):
            v = [str(x) for x in v]
        out[k] = v
    return out


def provision_to_chunks(p: Provision) -> list[dict]:
    cfg = config.DOCS[p.doc_id]
    act = cfg["act"]
    units = _units(p)
    if not units:
        return []
    pieces = pack_units(units)
    full_text = " ".join(units)
    title = ORDINAL_CLEAN.sub("", p.title).strip(" .—-") or ""
    label = _label(act, p)
    num = re.match(r"\d+", p.section_no.replace("sch1-", "").replace("sch2-form", ""))

    # provision-level enrichment shared by all parts of the provision
    eq = enrich.equivalents(act, p.section_no) if p.kind in ("section", "plain_language") else {}
    base = {
        "doc_id": p.doc_id, "act": act, "doc_name": cfg["name"], "act_no": cfg["act_no"], "act_year": cfg["year"],
        "law_domain": cfg["domain"], "status": cfg["status"], "source_type": cfg["source_type"],
        "source_file": cfg["source_file"], "superseded_by": cfg.get("superseded_by"), "replaces": cfg.get("replaces"),
        "effective_from": cfg.get("effective_from"), "repealed_on": cfg.get("repealed_on"),
        "chapter_no": p.chapter_no, "chapter_title": p.chapter_title.title() if p.chapter_title.isupper() else p.chapter_title,
        "part": p.part, "page": p.page,
        "section_no": p.section_no if p.kind in ("section", "plain_language", "rule") else None,
        "section_int": int(num.group()) if num and p.kind in ("section", "plain_language") else None,
        "section_title": title or None, "provision_kind": p.kind, "label": f"{act} {label}",
        "topics": enrich.topics(title, full_text), "cross_refs": enrich.cross_refs(full_text, p.section_no),
        "ocr_noisy": True if p.doc_id == "scr" else None,
    }
    if p.doc_id in ("bns", "ipc_txt", "ipc_csv", "bnss", "crpc_csv", "bsa") and p.kind in ("section", "plain_language"):
        base.update(enrich.parse_punishment(full_text))
    base.update(eq)
    base.update(p.extra)
    if p.doc_id == "scr":
        base["order_no"] = p.extra.get("order_no")
        base["rule_no"] = p.extra.get("rule_no")
    if p.kind == "schedule_row":
        base["section_no"] = p.extra.get("bns_section")
        base["section_int"] = int(re.match(r"\d+", p.extra["bns_section"]).group()) if p.extra.get("bns_section") else None

    header_bits = [f"{cfg['name']} ({act}) {label}"]
    if title:
        header_bits.append(title)
    elif p.extra.get("heading_hint"):
        header_bits.append(f'"{p.extra["heading_hint"]}…"')
    if p.chapter_title:
        header_bits.append(f"Chapter {p.chapter_no}: {base['chapter_title']}")
    if eq.get("equivalent_section"):
        header_bits.append(f"equivalent to {eq['equivalent_act']} {eq['equivalent_section']}")
    if eq.get("equivalent_sections"):
        header_bits.append(f"replaces {eq['equivalent_act']} " + ", ".join(eq["equivalent_sections"]))
    if cfg["status"] == "repealed":
        header_bits.append(f"repealed, replaced by {cfg['superseded_by']}")
    header = " | ".join(header_bits)

    chunks = []
    pieces = [x for x in pieces if count_tokens(x) >= 3 and x.strip() not in ("Offence:",)]
    for i, piece in enumerate(pieces):
        meta = dict(base)
        meta.update(enrich.chunk_flags(piece))
        meta.update({
            "chunk_index": i, "chunk_count": len(pieces), "chunk_type": _chunk_type(p, piece),
            "token_count": count_tokens(piece), "char_count": len(piece),
            "context_header": header,
        })
        text = piece
        if len(text.encode("utf-8")) > config.MAX_TEXT_BYTES_IN_METADATA:
            text = text[: config.MAX_TEXT_BYTES_IN_METADATA // 2]
        meta["text"] = text
        chunks.append({"embed_text": f"{header}\n{piece}", "metadata": _clean_meta(meta)})
    return chunks

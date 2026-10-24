#!/usr/bin/env python
"""Parse every source in data/raw -> data/processed/chunks.jsonl  (no network, no models needed)."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from legal_rag import config
from legal_rag.chunker import provision_to_chunks
from legal_rag.parsers import bns, bnss, bsa, csv_sources, ipc_txt, sc_rules

RAW = config.RAW_DIR
JOBS = [
    ("bns", lambda: bns.parse(RAW / config.DOCS["bns"]["source_file"])),
    ("bnss", lambda: bnss.parse(RAW / config.DOCS["bnss"]["source_file"])),
    ("bsa", lambda: bsa.parse(RAW / config.DOCS["bsa"]["source_file"])),
    ("ipc_txt", lambda: ipc_txt.parse(RAW / config.DOCS["ipc_txt"]["source_file"])),
    ("ipc_csv", lambda: csv_sources.parse_ipc(RAW / config.DOCS["ipc_csv"]["source_file"])),
    ("crpc_csv", lambda: csv_sources.parse_crpc(RAW / config.DOCS["crpc_csv"]["source_file"])),
    ("scr", lambda: sc_rules.parse(RAW / config.DOCS["scr"]["source_file"])),
]


def slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def main():
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    records, seen_ids, report = [], Counter(), {}
    for doc_id, job in JOBS:
        provs, info = job()
        n_before = len(records)
        for p in provs:
            for c in provision_to_chunks(p):
                m = c["metadata"]
                kind = {"plain_language": "plain", "schedule_row": "sch1", "form": "form"}.get(p.kind, "sec")
                base = f"{doc_id}-{kind}-{slug(p.section_no)}-{m['chunk_index']}"
                seen_ids[base] += 1
                cid = base if seen_ids[base] == 1 else f"{base}-dup{seen_ids[base]}"
                records.append({"id": cid, "embed_text": c["embed_text"], "metadata": m})
        report[doc_id] = {"provisions": len(provs), "chunks": len(records) - n_before, **{k: v for k, v in info.items() if k != "last_section"}}
        print(f"{doc_id:9s} provisions={len(provs):4d} chunks={len(records)-n_before:5d} {info}")
    with open(config.CHUNKS_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    toks = sorted(r["metadata"]["token_count"] for r in records)
    print(f"\nTOTAL chunks: {len(records)}  -> {config.CHUNKS_PATH}")
    print(f"tokens/chunk: min={toks[0]} median={toks[len(toks)//2]} p95={toks[int(len(toks)*.95)]} max={toks[-1]}")
    print("chunk types:", dict(Counter(r["metadata"]["chunk_type"] for r in records)))


if __name__ == "__main__":
    main()

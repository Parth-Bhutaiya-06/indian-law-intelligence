#!/usr/bin/env python
"""Quick QA: python scripts/inspect_chunks.py [doc_id|act] [section_no]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from legal_rag import config
R = [json.loads(l) for l in open(config.CHUNKS_PATH, encoding="utf-8")]
doc = sys.argv[1] if len(sys.argv) > 1 else None
sec = sys.argv[2] if len(sys.argv) > 2 else None
for r in R:
    m = r["metadata"]
    if (not doc or doc in (m["doc_id"], m["act"])) and (not sec or m.get("section_no") == sec):
        print("\n" + r["id"], {k: v for k, v in m.items() if k not in ("text", "context_header")})
        print(r["embed_text"][:700])

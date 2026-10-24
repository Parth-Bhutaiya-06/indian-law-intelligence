#!/usr/bin/env python
"""python scripts/ask.py "What is the punishment for murder?"   (or run with no args for a prompt loop)
   --act BNS|IPC|BNSS|CrPC|BSA|SCR   --status in_force|repealed   --show-sources"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from legal_rag import rag


def run(q, a):
    text, hits = rag.answer(q, a.top_k, a.act, a.status)
    print("\n" + text + "\n")
    if a.show_sources:
        for h in hits:
            print(f"  {h['score']:.3f}  {h['label']:22s} {h.get('section_title', '')[:60]}  [{h['chunk_type']}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--act")
    ap.add_argument("--status")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--show-sources", action="store_true")
    a = ap.parse_args()
    if a.question:
        return run(a.question, a)
    while True:
        q = input("question> ").strip()
        if q in ("", "exit", "quit"):
            break
        run(q, a)


if __name__ == "__main__":
    main()

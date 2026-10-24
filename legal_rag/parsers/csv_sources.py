"""Parsers for ipc_sections.csv and crpc_sections.csv (structured, one row per section)."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .common import Provision


def _read_csv_robust(path: Path) -> pd.DataFrame:
    """crpc_sections.csv is UTF-8 with a few stray cp1252 bytes: decode line by line."""
    import io

    raw = path.read_bytes()
    out = []
    for ln in raw.split(b"\n"):
        try:
            out.append(ln.decode("utf-8"))
        except UnicodeDecodeError:
            out.append(ln.decode("cp1252", errors="replace").replace("�", ""))
    return pd.read_csv(io.StringIO("\n".join(out)), dtype=str, keep_default_na=False)


# ----------------------------------------------------------------------------- IPC csv
def parse_ipc(path: Path) -> tuple[list[Provision], dict]:
    df = _read_csv_robust(path)
    provs, seen = [], set()
    for _, r in df.iterrows():
        sec = r["Section"].replace("IPC_", "").strip()
        desc = r["Description"].replace("\r", "")
        key = (sec, desc[:200])
        if key in seen:
            continue
        seen.add(key)
        split = re.split(r"\n\s*IPC\s+\S+\s+in Simple Words\s*\n", desc, maxsplit=1)
        legal = re.sub(r"^Description of IPC Section \S+\s*\n", "", split[0]).strip()
        simple = split[1].strip() if len(split) > 1 else ""
        extra = {"offence": r["Offense"].strip(), "punishment_summary": r["Punishment"].strip()}
        header = []
        if extra["offence"]:
            header.append(f"Offence: {extra['offence']}")
        if extra["punishment_summary"]:
            header.append(f"Punishment: {extra['punishment_summary']}")
        p = Provision(doc_id="ipc_csv", section_no=sec, title=extra["offence"][:160], kind="section", extra=extra)
        p.lines = header + legal.splitlines()
        provs.append(p)
        if simple:
            s = Provision(doc_id="ipc_csv", section_no=sec, title=extra["offence"][:160], kind="plain_language",
                          extra=dict(extra), lines=[f"Plain-language explanation of IPC section {sec}."] + simple.splitlines())
            provs.append(s)
    return provs, {"rows": len(df), "provisions": len(provs)}


# ----------------------------------------------------------------------------- CrPC csv
def parse_crpc(path: Path) -> tuple[list[Provision], dict]:
    df = _read_csv_robust(path)
    provs, skipped = [], 0
    for _, r in df.iterrows():
        sec = r["Section"].strip()
        desc = r["Description"].replace("\r", "").strip()
        if not sec or not desc:
            skipped += 1
            continue
        try:
            chapter_no = str(int(float(r["Chapter"])))
        except ValueError:
            chapter_no = r["Chapter"].strip()
        p = Provision(doc_id="crpc_csv", section_no=sec, title=r["Section _name"].strip().rstrip("."),
                      chapter_no=chapter_no, chapter_title=r["Chapter_name"].strip(), kind="section",
                      extra={"chapter_subtype": r["Chapter_subtype"].strip()} if r["Chapter_subtype"].strip() else {})
        p.lines = desc.splitlines()
        provs.append(p)
    return provs, {"rows": len(df), "skipped": skipped}

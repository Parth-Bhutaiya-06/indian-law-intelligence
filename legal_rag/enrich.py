"""Metadata enrichment: punishment parsing, cross references, topics, flags, old<->new section maps."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache

from . import config

NUMWORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
    "eighteen nineteen twenty".split())}
NUMWORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "hundred": 100})
_NUM = r"(\d+|" + "|".join(NUMWORDS) + r")"


def _n(tok: str) -> float:
    return float(tok) if tok.isdigit() else float(NUMWORDS[tok.lower()])


def parse_punishment(text: str) -> dict:
    t = text[:2500]
    out: dict = {}
    low = t.lower()
    if re.search(r"punished with death|sentence of death|or with death", low):
        out["punishment_death"] = True
    if re.search(r"imprisonment for life|imprisonment for the remainder", low):
        out["punishment_life"] = True
    ys = [_n(m.group(1)) for m in re.finditer(r"(?:may|which may) extend to " + _NUM + r" years?", t, re.I)]
    ys += [_n(m.group(1)) / 12 for m in re.finditer(r"(?:may|which may) extend to " + _NUM + r" months?", t, re.I)]
    if ys:
        out["max_imprisonment_years"] = round(max(ys), 2)
    mins = [_n(m.group(1)) for m in re.finditer(r"not be less than " + _NUM + r" years?", t, re.I)]
    if mins:
        out["min_imprisonment_years"] = min(mins)
    if re.search(r"\bfine\b", low):
        out["punishment_fine"] = True
    return out


_REF = re.compile(r"\bsections?\s+((?:\d{1,3}[A-Z]{0,2}(?:\s*\(\w{1,3}\))*\s*(?:,|and|to|or|\bor\b)?\s*)+)", re.I)
_NUMTOK = re.compile(r"\b(\d{1,3}[A-Z]{0,2})\b")


def cross_refs(text: str, self_no: str = "", limit: int = 15) -> list[str]:
    seen, out = set(), []
    for m in _REF.finditer(text):
        for n in _NUMTOK.findall(m.group(1)):
            if n != self_no and n not in seen:
                seen.add(n)
                out.append(n)
    return out[:limit]


TOPICS = {
    "murder_homicide": r"\bmurder|culpable homicide|death by negligence|dowry death",
    "hurt_assault": r"\bhurt\b|grievous|assault|criminal force|acid",
    "sexual_offences": r"\brape\b|sexual|modesty|stalking|voyeurism|outrage",
    "women_children": r"\bwoman|women|\bchild\b|children|dowry|cruelty by (?:husband|relative)|marriage",
    "theft_robbery": r"\btheft|robbery|dacoity|extortion|snatching|criminal misappropriation",
    "cheating_fraud": r"cheating|fraud|forgery|counterfeit|criminal breach of trust|dishonest",
    "property_trespass": r"trespass|mischief|house-breaking|criminal intimidation|arson",
    "state_security": r"sovereignty|waging war|sedition|terroris|organised crime|public tranquillity|unlawful assembly|riot",
    "public_servant": r"public servant|bribe|gratification",
    "false_evidence_justice": r"false evidence|perjury|fabricat|public justice|contempt",
    "defamation_speech": r"defam|obscen|insult|hate|promoting enmity",
    "general_exceptions": r"private defence|general exceptions|unsound mind|intoxication|necessity|accident|consent",
    "abetment_conspiracy": r"abet|conspiracy|common intention|attempt",
    "punishment_sentencing": r"punishment|sentence|fine\b|commutation|community service|solitary",
    "arrest": r"\barrest|custody|handcuff|police officer may",
    "bail_bonds": r"\bbail|bond|surety|anticipatory",
    "fir_investigation": r"first information|\bFIR\b|investigat|police report|chargesheet|charge-sheet|zero fir",
    "search_seizure": r"search warrant|\bsearch\b|seizure|seized|audio-video",
    "trial_procedure": r"\btrial|cognizance|charge\b|summons|warrant-case|summary trial|plea bargain|acquittal|discharge",
    "appeal_revision": r"\bappeal|revision|reference|review|quash",
    "evidence_admissibility": r"admissib|relevan|proof|burden of proof|presumption|estoppel",
    "confession_statement": r"confession|dying declaration|admission|statement made",
    "witness_examination": r"witness|examination-in-chief|cross-examination|re-examination|leading question",
    "electronic_evidence": r"electronic|digital|computer|certificate|hash|audio-video",
    "documents": r"\bdocument|secondary evidence|primary evidence|public document",
    "court_practice": r"registrar|special leave petition|petition|affidavit|advocate-on-record|vakalatnama|caveat|costs",
    "juvenile_minor": r"juvenile|minor|child in conflict",
    "victim_compensation": r"victim|compensation|witness protection",
}
_TOPIC_RE = {k: re.compile(v, re.I) for k, v in TOPICS.items()}


def topics(title: str, text: str, top: int = 6) -> list[str]:
    body = text[:2500]
    scored = []
    for k, rx in _TOPIC_RE.items():
        s = 3 * len(rx.findall(title)) + len(rx.findall(body))
        if s:
            scored.append((s, k))
    scored.sort(reverse=True)
    return [k for _, k in scored[:top]]


_CASE = re.compile(r"\bAIR\s+\d{4}\b|\(\d{4}\)\s*\d+\s*SCC|\bSCC\b|Cr\.?\s?L\.?J|\bSCR\b|\bSC Cr R\b|\bv\.\s+[A-Z]")


def case_citations(text: str) -> int:
    return len(_CASE.findall(text))


def chunk_flags(text: str) -> dict:
    f = {}
    if re.search(r"\bIllustrations?\b", text):
        f["has_illustrations"] = True
    if re.search(r"\bExceptions?\s*\d*\.?[—-]", text):
        f["has_exceptions"] = True
    if re.search(r"\bExplanations?\b", text):
        f["has_explanation"] = True
    if re.search(r"\bProvided (?:that|further)", text):
        f["has_proviso"] = True
    n = case_citations(text)
    if n:
        f["has_case_citations"] = True
        f["case_citation_count"] = n
    return f


# ------------------------------------------------------------------ old <-> new section maps
@lru_cache(maxsize=1)
def section_maps() -> dict:
    raw = json.loads(config.SECTION_MAPS_PATH.read_text())
    ipc, crpc = raw["ipc_to_bns"], raw["crpc_to_bnss"]
    rev_bns, rev_bnss = defaultdict(list), defaultdict(list)
    for o, n in ipc.items():
        rev_bns[n].append(o)
    for o, n in crpc.items():
        rev_bnss[n].append(o)
    return {"ipc": ipc, "crpc": crpc, "bns": dict(rev_bns), "bnss": dict(rev_bnss)}


def equivalents(act: str, section_no: str) -> dict:
    m = section_maps()
    base = section_no
    if act == "IPC" and base in m["ipc"]:
        return {"equivalent_act": "BNS", "equivalent_section": m["ipc"][base]}
    if act == "CrPC" and base in m["crpc"]:
        return {"equivalent_act": "BNSS", "equivalent_section": m["crpc"][base]}
    if act == "BNS" and base in m["bns"]:
        return {"equivalent_act": "IPC", "equivalent_sections": m["bns"][base]}
    if act == "BNSS" and base in m["bnss"]:
        return {"equivalent_act": "CrPC", "equivalent_sections": m["bnss"][base]}
    return {}

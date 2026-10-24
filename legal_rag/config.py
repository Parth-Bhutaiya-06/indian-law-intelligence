"""Central configuration: paths, models, Pinecone settings, and the document registry."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
EMB_PATH = PROCESSED_DIR / "embeddings.npy"
EMB_IDS_PATH = PROCESSED_DIR / "embedding_ids.json"
SECTION_MAPS_PATH = ROOT / "data" / "section_maps.json"

# ---------------------------------------------------------------- embeddings (local, no API)
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))  # must match the model! (see MODEL_INFO)
MODEL_INFO = {
    # model: (dimension, max_tokens, query_prefix, doc_prefix)
    "BAAI/bge-base-en-v1.5": (768, 512, "Represent this sentence for searching relevant passages: ", ""),
    "BAAI/bge-small-en-v1.5": (384, 512, "Represent this sentence for searching relevant passages: ", ""),
    "BAAI/bge-large-en-v1.5": (1024, 512, "Represent this sentence for searching relevant passages: ", ""),
    "intfloat/e5-base-v2": (768, 512, "query: ", "passage: "),
    "sentence-transformers/all-mpnet-base-v2": (768, 384, "", ""),
    "sentence-transformers/all-MiniLM-L6-v2": (384, 256, "", ""),
}
_info = MODEL_INFO.get(EMBED_MODEL)
if _info:
    EMBED_DIM = _info[0]
QUERY_PREFIX = _info[2] if _info else ""
DOC_PREFIX = _info[3] if _info else ""
MODEL_MAX_TOKENS = _info[1] if _info else 512

# ---------------------------------------------------------------- chunking
MAX_CHUNK_TOKENS = 380      # body tokens; the contextual header adds ~30, model limit is 512
OVERLAP_TOKENS = 40         # only a short trailing unit is carried over between split parts
MIN_CHUNK_TOKENS = 25       # tiny tails are merged into the previous chunk
MAX_TEXT_BYTES_IN_METADATA = 30000  # Pinecone allows 40KB metadata per vector

# ---------------------------------------------------------------- Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "indian-law")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "legal")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
PINECONE_METRIC = "cosine"  # embeddings are L2-normalised, so cosine == dot product

# ---------------------------------------------------------------- Groq (generation only)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# ---------------------------------------------------------------- document registry
# act = value of the `act` metadata field (what users filter on).
DOCS = {
    "bns": dict(
        act="BNS", name="Bharatiya Nyaya Sanhita, 2023", act_no="45 of 2023", year=2023,
        domain="substantive_criminal_law", status="in_force", effective_from="2024-07-01",
        replaces="IPC", source_file="bns_2023_as_on_2025.txt", source_type="statute_text",
    ),
    "bnss": dict(
        act="BNSS", name="Bharatiya Nagarik Suraksha Sanhita, 2023", act_no="46 of 2023", year=2023,
        domain="criminal_procedure", status="in_force", effective_from="2024-07-01",
        replaces="CrPC", source_file="bnss_2023_gazette.txt", source_type="statute_text",
    ),
    "bsa": dict(
        act="BSA", name="Bharatiya Sakshya Adhiniyam, 2023", act_no="47 of 2023", year=2023,
        domain="evidence_law", status="in_force", effective_from="2024-07-01",
        replaces="Indian Evidence Act, 1872", source_file="bsa_2023_gazette.pdf", source_type="statute_text",
    ),
    "ipc_txt": dict(
        act="IPC", name="Indian Penal Code, 1860", act_no="45 of 1860", year=1860,
        domain="substantive_criminal_law", status="repealed", repealed_on="2024-07-01",
        superseded_by="BNS", source_file="ipc_annotated.txt", source_type="annotated_statute",
    ),
    "ipc_csv": dict(
        act="IPC", name="Indian Penal Code, 1860", act_no="45 of 1860", year=1860,
        domain="substantive_criminal_law", status="repealed", repealed_on="2024-07-01",
        superseded_by="BNS", source_file="ipc_sections.csv", source_type="structured_summary",
    ),
    "crpc_csv": dict(
        act="CrPC", name="Code of Criminal Procedure, 1973", act_no="2 of 1974", year=1973,
        domain="criminal_procedure", status="repealed", repealed_on="2024-07-01",
        superseded_by="BNSS", source_file="crpc_sections.csv", source_type="statute_text",
    ),
    "scr": dict(
        act="SCR", name="Supreme Court Rules, 2013", act_no="G.S.R. 368(E)", year=2013,
        domain="court_rules", status="in_force", effective_from="2014-08-19",
        source_file="supreme_court_rules_2013.txt", source_type="court_rules",
    ),
}

# Which act aliases a user may type -> `act` metadata values
ACT_ALIASES = {
    "BNS": ["bns", "bharatiya nyaya sanhita"],
    "BNSS": ["bnss", "bharatiya nagarik suraksha sanhita"],
    "BSA": ["bsa", "bharatiya sakshya adhiniyam", "evidence act", "indian evidence act"],
    "IPC": ["ipc", "indian penal code"],
    "CrPC": ["crpc", "cr.p.c", "cr.p.c.", "code of criminal procedure"],
    "SCR": ["supreme court rules", "sc rules"],
}

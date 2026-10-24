# Indian Criminal-Law RAG (BNS · BNSS · BSA · IPC · CrPC · Supreme Court Rules)

Local sentence-transformer embeddings (no embedding API) → Pinecone (vector DB) → Groq (open LLM) for answers.

## Pinecone index settings
| Setting | Value |
|---|---|
| Dimension | **768** (BAAI/bge-base-en-v1.5) |
| Metric | **cosine** (vectors are normalised) |
| Type / cloud / region | Serverless · AWS · us-east-1 (free Starter plan region) |
| Namespace | `legal` (one namespace; filter by metadata `act`, `status`, ...) |
The script creates the index for you; if you create it by hand use exactly the above.
Change model -> change dimension: bge-small = 384, bge-large = 1024, e5-base = 768 (set `EMBED_MODEL`).

## Run
```bash
pip install -r requirements.txt
cp .env.example .env            # add PINECONE_API_KEY and GROQ_API_KEY
python scripts/build_chunks.py  # parse + chunk + metadata -> data/processed/chunks.jsonl
python scripts/upload_pinecone.py --dry-run   # (optional) embeds only
python scripts/upload_pinecone.py             # embed + create index + upsert
python scripts/ask.py "What is the punishment for murder?" --show-sources
python scripts/ask.py "section 35 BNSS arrest without warrant"
python scripts/ask.py "Order XXI rule 5" 
```
Useful: `python scripts/inspect_chunks.py BNS 103` to eyeball a chunk and its metadata.

## Metadata on every vector (filterable)
act, doc_id, doc_name, status (in_force/repealed), superseded_by/replaces, law_domain, source_type, chapter_no/title, part,
section_no, section_int (range filters), section_title, label, page, chunk_type (provision | illustrations | case_law_commentary |
plain_language | schedule_row | form | rule | schedule), chunk_index/chunk_count, topics[], cross_refs[], punishment_death/life/fine,
max/min_imprisonment_years, has_illustrations/exceptions/explanation/proviso/case_citations, equivalent_act/section(s) (IPC<->BNS,
CrPC<->BNSS: partial map in data/section_maps.json), cognizable/bailable (BNSS First Schedule rows), order_no/rule_no (SCR), text.

## Known limits (see data quality notes in the chat)
BNSS section titles are not recoverable from this extraction (a `heading_hint` is stored instead); Supreme Court Rules is OCR-noisy
(some orders/rules merged); the IPC/BNS equivalence map is partial - verify and extend.

## GUI
```bash
streamlit run app.py
```
Tabs: **Ask** (chat with cited sources, filters for act/status, adjustable model/top-k) and **Browse sections** (offline lookup by act + section number or keyword).

"""Indian Law Intelligence — professional Streamlit dashboard.
Run with: python -m streamlit run app.py
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from legal_rag import config, rag

st.set_page_config(
    page_title="Indian Law Intelligence",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

NAV_ITEMS = ["Overview", "Ask the Law", "Section Explorer", "Offence Finder"]
ACTS = ["BNS", "BNSS", "BSA", "IPC", "CrPC", "SCR"]
ACT_NAMES = {
    "BNS": "Bharatiya Nyaya Sanhita, 2023",
    "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "BSA": "Bharatiya Sakshya Adhiniyam, 2023",
    "IPC": "Indian Penal Code (repealed)",
    "CrPC": "Code of Criminal Procedure (repealed)",
    "SCR": "Supreme Court Rules, 2013",
}
COLORS = {
    "navy": "#17324D", "blue": "#245B82", "blue2": "#3479A8",
    "teal": "#1A8A83", "amber": "#D88A32", "red": "#C64B4B",
    "ink": "#172B3A", "muted": "#6B7C8F", "line": "#E2E8F0",
    "surface": "#FFFFFF", "canvas": "#F4F7FB", "pale": "#EAF1F8",
}

st.markdown(f"""
<style>
:root {{ --navy:{COLORS['navy']}; --blue:{COLORS['blue']}; --line:{COLORS['line']}; }}
.stApp {{ background:{COLORS['canvas']}; color:{COLORS['ink']}; }}
[data-testid="stHeader"] {{ background:rgba(244,247,251,.96); }}
[data-testid="stAppViewContainer"] .main .block-container {{ max-width:1500px; padding:1.1rem 2.1rem 3rem; }}
#MainMenu, footer {{ visibility:hidden; }}
[data-testid="stSidebar"] {{ display:none; }}
.top-brand {{ display:flex; align-items:center; gap:13px; padding:6px 0 17px; }}
.brand-mark {{ width:44px; height:44px; border-radius:12px; display:flex; align-items:center; justify-content:center; color:white; background:linear-gradient(140deg,#17324D,#3479A8); font-size:23px; font-weight:700; box-shadow:0 5px 14px #17324d20; }}
.brand-title {{ font-size:1.28rem; font-weight:750; color:{COLORS['navy']}; letter-spacing:-.035em; line-height:1.2; }}
.brand-sub {{ color:{COLORS['muted']}; font-size:.79rem; margin-top:3px; }}
.header-right {{ margin-left:auto; color:{COLORS['muted']}; font-size:.78rem; text-align:right; }}
.rule {{ height:1px; background:{COLORS['line']}; margin:0 0 17px; }}
/* Horizontal navigation */
div[data-testid="stRadio"] > label {{ display:none; }}
div[data-testid="stRadio"] > div {{ gap:8px; border-bottom:1px solid {COLORS['line']}; padding:0 0 13px; flex-wrap:wrap; }}
div[data-testid="stRadio"] > div > label {{ border:1px solid transparent; background:transparent; padding:9px 16px; border-radius:9px; color:{COLORS['muted']}; font-weight:650; font-size:.9rem; transition:all .15s ease; }}
div[data-testid="stRadio"] > div > label:has(input:checked) {{ background:{COLORS['navy']}; color:#fff !important; border-color:{COLORS['navy']}; box-shadow:0 3px 8px #17324d20; }}
div[data-testid="stRadio"] > div > label > div:first-child {{ display:none; }}
.page-heading {{ display:flex; align-items:flex-end; justify-content:space-between; gap:15px; margin:22px 0 16px; }}
.page-title {{ color:{COLORS['navy']}; font-size:1.75rem; font-weight:780; letter-spacing:-.045em; margin:0; }}
.page-desc {{ color:{COLORS['muted']}; font-size:.9rem; margin-top:5px; }}
.section-title {{ color:{COLORS['navy']}; font-weight:720; font-size:1.05rem; margin:9px 0 10px; }}
.eyebrow {{ color:{COLORS['blue2']}; text-transform:uppercase; font-size:.7rem; letter-spacing:.12em; font-weight:750; }}
.kpi-card {{ background:#fff; border:1px solid {COLORS['line']}; border-radius:13px; padding:17px 18px; min-height:112px; box-shadow:0 2px 6px rgba(23,50,77,.025); }}
.kpi-label {{ color:{COLORS['muted']}; font-size:.78rem; font-weight:650; margin-bottom:10px; }}
.kpi-value {{ color:{COLORS['navy']}; font-size:1.85rem; line-height:1.05; font-weight:780; letter-spacing:-.04em; }}
.kpi-foot {{ color:{COLORS['muted']}; font-size:.72rem; margin-top:9px; }}
.panel {{ background:white; border:1px solid {COLORS['line']}; border-radius:13px; padding:16px 18px; }}
.source-card {{ background:#fff; border:1px solid {COLORS['line']}; border-left:4px solid {COLORS['blue2']}; border-radius:10px; padding:12px 15px; margin:8px 0; }}
.source-card.old {{ border-left-color:{COLORS['red']}; }}
.source-title {{ font-weight:720; color:{COLORS['ink']}; font-size:.91rem; }}
.source-meta {{ color:{COLORS['muted']}; font-size:.76rem; margin-top:6px; }}
.pill {{ display:inline-block; background:{COLORS['pale']}; color:{COLORS['blue']}; padding:3px 8px; border-radius:5px; font-size:.69rem; margin-right:6px; font-weight:650; }}
.pill-green {{ background:#E7F5EF; color:#207653; }} .pill-red {{ background:#FCEBEC; color:#B23A45; }}
.notice {{ background:#FFF8E9; border:1px solid #F4E2B9; color:#76551B; border-radius:9px; padding:11px 14px; font-size:.83rem; }}
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"], div[data-testid="stMultiSelect"] div[data-baseweb="select"] {{ border-radius:8px; }}
.stButton > button, .stDownloadButton > button {{ border-radius:8px; font-weight:650; min-height:40px; }}
.stButton > button[kind="primary"] {{ background:{COLORS['navy']}; border-color:{COLORS['navy']}; }}
[data-testid="stDataFrame"] {{ border:1px solid {COLORS['line']}; border-radius:10px; overflow:hidden; }}
div[data-testid="stExpander"] {{ border:1px solid {COLORS['line']}; border-radius:9px; background:#fff; }}
[data-testid="stChatMessage"] {{ background:#fff; border:1px solid {COLORS['line']}; border-radius:12px; padding:12px 15px; }}
div[data-testid="stMetric"] {{ background:#fff; border:1px solid {COLORS['line']}; padding:13px 15px; border-radius:10px; }}
.small-muted {{ color:{COLORS['muted']}; font-size:.78rem; }}
@media(max-width:800px) {{ [data-testid="stAppViewContainer"] .main .block-container {{ padding:1rem .85rem 2rem; }} .page-title {{ font-size:1.45rem; }} .kpi-value {{ font-size:1.45rem; }} }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    """Load chunk metadata safely from the local JSONL index."""
    path = Path(config.CHUNKS_PATH)
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                obj = json.loads(line)
                rows.append(obj.get("metadata", obj))
            except (json.JSONDecodeError, TypeError):
                continue
    frame = pd.DataFrame(rows)
    defaults = {
        "act": "Unknown", "status": "unknown", "section_no": "",
        "section_title": "", "chunk_type": "unknown", "token_count": 0,
        "topics": None, "provision_kind": "unknown", "max_imprisonment_years": None,
        "punishment_death": False, "punishment_life": False, "punishment_fine": False,
        "chapter_title": "", "chunk_index": 0, "chunk_count": 1, "doc_id": "",
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default
    for column in ("punishment_death", "punishment_life", "punishment_fine"):
        frame[column] = frame[column].fillna(False).astype(bool)
    frame["token_count"] = pd.to_numeric(frame["token_count"], errors="coerce").fillna(0)
    frame["max_imprisonment_years"] = pd.to_numeric(frame["max_imprisonment_years"], errors="coerce")
    return frame


@st.cache_resource(show_spinner="Loading local embedding model…")
def warm_index():
    from legal_rag import embedder, store
    embedder.get_model()
    return store.get_index()


def page_heading(title: str, description: str, eyebrow: str = "LEGAL RESEARCH WORKSPACE"):
    st.markdown(
        f'<div class="page-heading"><div><div class="eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="page-title">{html.escape(title)}</div><div class="page-desc">{html.escape(description)}</div></div></div>',
        unsafe_allow_html=True,
    )


def kpi(value, label, foot=""):
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{html.escape(str(label))}</div>'
        f'<div class="kpi-value">{html.escape(str(value))}</div><div class="kpi-foot">{html.escape(str(foot))}</div></div>',
        unsafe_allow_html=True,
    )


def make_chart(fig, height=320):
    """Apply consistent chart spacing so titles and legends never collide."""
    fig.update_layout(
        height=height,
        # Reserve enough room above the plotting area for both title and legend.
        margin=dict(l=14, r=14, t=100, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=COLORS["ink"], size=12),
        title=dict(
            font=dict(size=14, color=COLORS["navy"]),
            x=0.02,
            xanchor="left",
            y=0.99,
            yanchor="top",
        ),
        # Keep the legend on its own row underneath the chart title.
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.14,
            x=0.02,
            xanchor="left",
            title_text="",
            traceorder="normal",
        ),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["line"], zeroline=False)
    fig.update_yaxes(gridcolor="#EDF1F6", zeroline=False)
    return fig


def source_card(number: int, hit: dict):
    old = hit.get("status") == "repealed"
    label = html.escape(str(hit.get("label") or f"Source {number}"))
    title = html.escape(str(hit.get("section_title") or "Untitled provision")[:120])
    status_label = "Repealed" if old else ("In force" if hit.get("status") == "in_force" else str(hit.get("status", "Unknown")))
    status_class = "pill-red" if old else "pill-green"
    chunk_type = html.escape(str(hit.get("chunk_type", "passage")))
    score = hit.get("score", 0)
    try:
        score_text = f"{float(score):.3f}"
    except (TypeError, ValueError):
        score_text = "—"
    eq = ""
    if hit.get("equivalent_section"):
        eq = f" · Equivalent: {html.escape(str(hit.get('equivalent_act', '')))} {html.escape(str(hit['equivalent_section']))}"
    elif hit.get("equivalent_sections"):
        eq = f" · Equivalent: {html.escape(str(hit.get('equivalent_act', '')))} {html.escape(', '.join(map(str, hit['equivalent_sections'])))}"
    st.markdown(
        f'<div class="source-card {"old" if old else ""}"><div class="source-title">[{number}] {label} — {title}</div>'
        f'<div class="source-meta"><span class="pill {status_class}">{html.escape(status_label)}</span>'
        f'<span class="pill">{chunk_type}</span>Relevance {score_text}{eq}</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander(f"Read passage {number}"):
        st.write(hit.get("text", "No passage text was returned."))
        metadata = {key: value for key, value in hit.items() if key not in ("text", "context_header", "id")}
        st.json(metadata, expanded=False)


def chunks_for(frame: pd.DataFrame, act: str, section: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    match = frame[(frame["act"].astype(str) == act) & (frame["section_no"].astype(str).str.upper() == section.strip().upper())]
    sort_cols = [col for col in ("doc_id", "chunk_type", "chunk_index") if col in match.columns]
    return match.sort_values(sort_cols) if sort_cols else match


def render_section(frame: pd.DataFrame, act: str, section: str):
    if frame.empty:
        st.info(f"No indexed passage found for {act} Section {section}.")
        return
    first = frame.iloc[0]
    st.markdown(f"### {act} · Section {section}")
    st.markdown(f"**{first.get('section_title') or 'Provision details'}**")
    status = str(first.get("status", "unknown"))
    pill_class = "pill-red" if status == "repealed" else "pill-green"
    st.markdown(f'<span class="pill {pill_class}">{html.escape(status)}</span> <span class="pill">{html.escape(str(first.get("chapter_title", "Chapter not recorded")))}</span>', unsafe_allow_html=True)
    for _, row in frame.iterrows():
        kind = str(row.get("chunk_type", "passage"))
        idx = int(row.get("chunk_index", 0) or 0) + 1
        count = int(row.get("chunk_count", 1) or 1)
        with st.expander(f"{kind.replace('_', ' ').title()} · part {idx}/{count}", expanded=kind != "case_law_commentary"):
            st.write(row.get("text", "Text unavailable"))
    refs = first.get("cross_refs")
    if isinstance(refs, list) and refs:
        st.caption("Cross-references: " + ", ".join(map(str, refs)))


def render_overview(df: pd.DataFrame, chosen_acts: list[str]):
    page_heading("Legal intelligence overview", "A consolidated view of your indexed acts, sections and source coverage.", "WORKSPACE / OVERVIEW")
    if df.empty:
        st.error(f"No chunks were loaded. Check that the file exists: {config.CHUNKS_PATH}")
        return
    data = df[df["act"].isin(chosen_acts)] if chosen_acts else df.iloc[0:0]
    total_chunks = len(data)
    total_sections = data[["act", "section_no"]].drop_duplicates().shape[0] if total_chunks else 0
    in_force_pct = (data["status"].eq("in_force").mean() * 100) if total_chunks else 0
    avg_tokens = int(data["token_count"].mean()) if total_chunks else 0
    a, b, c, d = st.columns(4, gap="medium")
    with a: kpi(f"{total_chunks:,}", "Indexed passages", "After selected act filters")
    with b: kpi(f"{data['act'].nunique():,}", "Acts represented", "Statutes and rule books")
    with c: kpi(f"{total_sections:,}", "Distinct act-sections", "Unique section references")
    with d: kpi(f"{in_force_pct:.0f}%", "Passages in force", f"Average chunk length: {avg_tokens:,} tokens")

    st.markdown('<div class="section-title">Collection analytics</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        by_act = data.groupby(["act", "status"], dropna=False).size().reset_index(name="Passages")
        fig = px.bar(by_act, x="act", y="Passages", color="status", barmode="stack", text_auto=True,
                     title="Indexed passages by act", color_discrete_map={"in_force": COLORS["blue"], "repealed": COLORS["red"], "unknown": "#9AA8B7"})
        st.plotly_chart(make_chart(fig, 340), use_container_width=True)
    with right:
        types = data["chunk_type"].fillna("unknown").astype(str).value_counts().rename_axis("Chunk type").reset_index(name="Count")
        fig = px.pie(types, names="Chunk type", values="Count", hole=.68, title="Content composition", color_discrete_sequence=[COLORS["blue"], COLORS["teal"], COLORS["amber"], "#8C9DB0", "#A5B4FC"])
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(make_chart(fig, 340), use_container_width=True)

    left, right = st.columns(2, gap="large")
    with left:
        topic_frame = data.explode("topics") if "topics" in data.columns else pd.DataFrame()
        if not topic_frame.empty and "topics" in topic_frame.columns:
            topic_frame = topic_frame.dropna(subset=["topics"])
            topic_counts = topic_frame["topics"].astype(str).value_counts().head(12).sort_values().reset_index()
            topic_counts.columns = ["Topic", "Passages"]
            fig = px.bar(topic_counts, x="Passages", y="Topic", orientation="h", title="Most represented topics", text_auto=True, color_discrete_sequence=[COLORS["teal"]])
            st.plotly_chart(make_chart(fig, 360), use_container_width=True)
        else:
            st.info("Topic metadata is not available for the current selection.")
    with right:
        fig = px.histogram(data, x="token_count", color="act", nbins=35, title="Passage length distribution", color_discrete_sequence=[COLORS["blue"], COLORS["teal"], COLORS["amber"], "#8C78C8", "#D16D6D"])
        st.plotly_chart(make_chart(fig, 360), use_container_width=True)

    st.markdown('<div class="section-title">Act coverage</div>', unsafe_allow_html=True)
    coverage = data.groupby("act").agg(Passages=("section_no", "size"), Sections=("section_no", "nunique"), Avg_tokens=("token_count", "mean")).reset_index()
    coverage["Avg_tokens"] = coverage["Avg_tokens"].round(0).astype("Int64")
    st.dataframe(coverage.rename(columns={"act": "Act", "Passages": "Indexed passages", "Sections": "Distinct section labels", "Avg_tokens": "Average tokens"}), use_container_width=True, hide_index=True)


def render_ask(acts_filter: list[str], status_filter: str, top_k: int, model: str, temperature: float):
    page_heading("Ask the law", "Ask a question in plain language and inspect the legal passages used to answer it.", "RESEARCH / AI ASSISTANT")
    st.markdown('<div class="notice">Research support only. Check the original legislation and consult a qualified lawyer for advice on a specific case.</div>', unsafe_allow_html=True)
    st.markdown(" ")
    with st.expander("Example questions", expanded=False):
        st.write("- What is the punishment for murder under BNS?\n- Explain BNSS section 35.\n- Compare IPC 420 with its BNS equivalent.\n- What do the Supreme Court Rules say about Order XXI Rule 5?")
    st.session_state.setdefault("legal_chat_history", [])
    for turn in st.session_state.legal_chat_history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.markdown(turn["answer"])
            st.caption(f"Retrieval {turn['retrieval_seconds']:.1f}s · Generation {turn['generation_seconds']:.1f}s · {len(turn['hits'])} passages")
            with st.expander(f"Sources used ({len(turn['hits'])})"):
                for idx, hit in enumerate(turn["hits"], 1): source_card(idx, hit)
    question = st.chat_input("Ask about an Indian law, section, offence or court rule…", key="law_question")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            try:
                index = warm_index()
                start = time.time()
                hits = []
                selected_acts = acts_filter or [None]
                selected_status = None if status_filter == "Any status" else status_filter
                with st.spinner("Searching the legal index…"):
                    for act in selected_acts:
                        hits.extend(rag.retrieve(question, top_k, act, selected_status, index=index))
                    unique_hits = {hit.get("id", json.dumps(hit, sort_keys=True, default=str)): hit for hit in hits}
                    hits = sorted(unique_hits.values(), key=lambda hit: float(hit.get("score", 0) or 0), reverse=True)[:top_k + 4]
                retrieved = time.time()
                if not config.GROQ_API_KEY:
                    raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file and restart Streamlit.")
                from groq import Groq
                with st.spinner("Drafting an answer from retrieved passages…"):
                    response = Groq(api_key=config.GROQ_API_KEY).chat.completions.create(
                        model=model, temperature=temperature, max_tokens=1200,
                        messages=[{"role": "system", "content": rag.SYSTEM},
                                  {"role": "user", "content": f"CONTEXT:\n{rag.build_context(hits)}\n\nQUESTION: {question}"}],
                    )
                answer = response.choices[0].message.content or "No answer was returned."
                finished = time.time()
                st.markdown(answer)
                st.caption(f"Retrieval {retrieved-start:.1f}s · Generation {finished-retrieved:.1f}s · {len(hits)} passages")
                with st.expander(f"Sources used ({len(hits)})", expanded=True):
                    if hits:
                        for idx, hit in enumerate(hits, 1): source_card(idx, hit)
                    else:
                        st.warning("No source passages were returned. Treat the answer as unavailable until relevant sources are found.")
                st.session_state.legal_chat_history.append({"question": question, "answer": answer, "hits": hits,
                    "retrieval_seconds": retrieved-start, "generation_seconds": finished-retrieved})
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")
                st.caption("Check your .env keys, model name, Pinecone connection and network before retrying.")
    if st.session_state.legal_chat_history:
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Clear conversation", use_container_width=True):
                st.session_state.legal_chat_history = []
                st.rerun()
        with c2:
            markdown = "\n\n---\n\n".join(f"## Question\n{turn['question']}\n\n## Answer\n{turn['answer']}" for turn in st.session_state.legal_chat_history)
            st.download_button("Export conversation (.md)", markdown, "legal_research_conversation.md", mime="text/markdown", use_container_width=True)


def render_explorer(df: pd.DataFrame):
    page_heading("Section explorer", "Read a provision, inspect its indexed passages and compare mapped old/new legislation.", "RESEARCH / STATUTE EXPLORER")
    c1, c2, c3 = st.columns([1.1, 1, 2.1], gap="medium")
    with c1:
        act = st.selectbox("Legislation", ACTS, index=0, format_func=lambda value: f"{value} · {ACT_NAMES[value]}", key="explorer_act")
    with c2:
        section = st.text_input("Section number", value="103", key="explorer_section", placeholder="e.g. 103")
    with c3:
        compare = st.toggle("Compare mapped equivalent", value=True, help="Uses equivalent-section metadata already stored in your indexed chunks.")
    if not section.strip():
        st.info("Enter a section number to explore the indexed provisions.")
        return
    left = chunks_for(df, act, section)
    if left.empty:
        st.warning("This section was not found in the current local index. Check the act and section number.")
        return
    first = left.iloc[0]
    equivalent_act = first.get("equivalent_act")
    equivalent_section = first.get("equivalent_section")
    equivalent_sections = first.get("equivalent_sections")
    if not (isinstance(equivalent_section, str) and equivalent_section.strip()) and isinstance(equivalent_sections, list) and equivalent_sections:
        equivalent_section = equivalent_sections[0]
    if compare and isinstance(equivalent_act, str) and equivalent_act in ACTS and isinstance(equivalent_section, str):
        left_col, right_col = st.columns(2, gap="large")
        with left_col: render_section(left, act, section.upper())
        with right_col:
            right = chunks_for(df, equivalent_act, equivalent_section)
            render_section(right, equivalent_act, equivalent_section)
    else:
        render_section(left, act, section.upper())
        if compare:
            st.info("No mapped equivalent is recorded for this section in the current index.")
    st.markdown('<div class="section-title">Section metadata</div>', unsafe_allow_html=True)
    visible = [col for col in ["act", "section_no", "section_title", "chapter_title", "status", "provision_kind", "topics", "cross_refs"] if col in left.columns]
    # Convert list/dict metadata to readable strings before drop_duplicates().
    # Pandas cannot hash Python lists, which caused the Section Explorer error.
    display_df = left[visible].copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].map(
            lambda value: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (list, dict))
            else value
        )
    display_df = display_df.drop_duplicates().reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_offence_finder(df: pd.DataFrame):
    page_heading("Offence finder", "Filter indexed BNS and IPC provisions by topic, imprisonment and punishment indicators.", "RESEARCH / OFFENCE LOOKUP")
    if df.empty:
        st.error("No indexed data is available. Check the chunks file path.")
        return
    base = df[(df["provision_kind"].isin(["section", "plain_language"])) & (df["act"].isin(["BNS", "IPC"]))].copy()
    if base.empty:
        st.warning("No BNS/IPC rows with section or plain-language provision metadata were found.")
        return
    base = base.drop_duplicates(["act", "section_no", "chunk_type"])
    topic_values = base.explode("topics")["topics"].dropna().astype(str).unique().tolist() if "topics" in base else []
    topic_values = sorted(topic_values)
    f1, f2, f3, f4 = st.columns([1, 1.5, 1.4, 1.6], gap="medium")
    with f1: selected_acts = st.multiselect("Act", ["BNS", "IPC"], default=["BNS"], key="offence_acts")
    with f2: selected_topics = st.multiselect("Topic", topic_values, key="offence_topics", placeholder="All topics")
    with f3: max_years = st.slider("Maximum imprisonment (years)", 0, 30, 30, key="offence_years")
    with f4: punishments = st.multiselect("Punishment includes", ["Death", "Life imprisonment", "Fine"], key="offence_punishments")
    result = base[base["act"].isin(selected_acts)]
    if selected_topics:
        result = result[result["topics"].apply(lambda values: isinstance(values, list) and any(topic in values for topic in selected_topics))]
    if max_years < 30:
        result = result[result["max_imprisonment_years"].isna() | (result["max_imprisonment_years"] <= max_years)]
    if "Death" in punishments: result = result[result["punishment_death"]]
    if "Life imprisonment" in punishments: result = result[result["punishment_life"]]
    if "Fine" in punishments: result = result[result["punishment_fine"]]
    columns = ["act", "section_no", "section_title", "max_imprisonment_years", "punishment_death", "punishment_life", "punishment_fine", "topics", "status"]
    columns = [column for column in columns if column in result.columns]
    show = result[columns].copy()
    st.markdown('<div class="section-title">Matching provisions</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a: kpi(f"{len(show):,}", "Matching indexed rows", "After current filters")
    with b: kpi(f"{show['section_no'].nunique():,}" if "section_no" in show else "0", "Distinct section labels", "Within filtered results")
    with c: kpi(f"{show['act'].nunique():,}" if "act" in show else "0", "Acts in results", "BNS / IPC")
    rename = {"act": "Act", "section_no": "Section", "section_title": "Provision", "max_imprisonment_years": "Max years", "punishment_death": "Death", "punishment_life": "Life imprisonment", "punishment_fine": "Fine", "topics": "Topics", "status": "Status"}
    st.dataframe(show.rename(columns=rename), use_container_width=True, hide_index=True, height=500)
    st.download_button("Download filtered results (CSV)", show.to_csv(index=False).encode("utf-8-sig"), "offence_finder_results.csv", mime="text/csv")


# App header and horizontal navigation
st.markdown(f"""
<div class="top-brand">
  <div class="brand-mark">§</div>
  <div><div class="brand-title">Indian Law Intelligence</div>
  <div class="brand-sub">Legal research · Statute intelligence · Source-grounded answers</div></div>
  <div class="header-right">INDIA<br><strong>Research workspace</strong></div>
</div><div class="rule"></div>
""", unsafe_allow_html=True)

selected_page = st.radio("Primary navigation", NAV_ITEMS, horizontal=True, label_visibility="collapsed", key="primary_navigation")

# Compact shared controls, shown below the main navigation.
with st.expander("Search preferences", expanded=False):
    f1, f2, f3, f4 = st.columns([1.5, 1.3, 1.1, 1.4], gap="medium")
    with f1:
        acts_filter = st.multiselect("Limit search to acts", ACTS, default=[], placeholder="All acts", key="global_acts")
    with f2:
        status_filter = st.selectbox("Legal status", ["Any status", "in_force", "repealed"], index=0, key="global_status")
    with f3:
        top_k = st.slider("Retrieved passages", 3, 15, 8, key="global_top_k")
    with f4:
        model = st.text_input("Groq model", value=config.GROQ_MODEL, key="global_model")
    temperature = st.slider("Answer creativity", 0.0, 1.0, 0.1, 0.05, key="global_temperature")

df = load_df()
if selected_page == "Overview":
    overview_acts = st.multiselect("Filter overview by act", ACTS, default=ACTS, key="overview_acts")
    render_overview(df, overview_acts)
elif selected_page == "Ask the Law":
    render_ask(acts_filter, status_filter, top_k, model.strip() or config.GROQ_MODEL, temperature)
elif selected_page == "Section Explorer":
    render_explorer(df)
elif selected_page == "Offence Finder":
    render_offence_finder(df)

st.markdown("<div class='rule' style='margin-top:28px'></div><div class='small-muted'>Indian Law Intelligence · Answers are based on retrieved indexed passages and are not legal advice.</div>", unsafe_allow_html=True)

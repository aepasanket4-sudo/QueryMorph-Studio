import io
import sqlite3
import streamlit as st
import pandas as pd
from data_loader import (
    load_file_to_dataframes,
    save_dataframes_to_sqlite,
    get_database_schema,
    export_table
)
from sql_engine import SQLAgent, DEFAULT_GEMINI_KEY, DEFAULT_GROQ_KEY

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="QueryMorph Studio | AI Data Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ULTRA-MODERN NIGHT MODE DESIGN CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Night Mode Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #F8FAFC !important;
    }

    .stApp {
        background-color: #0B0F19 !important;
    }

    /* Top Studio Header */
    .studio-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 0rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .studio-title {
        font-size: 1.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 40%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .studio-subtitle {
        margin: 4px 0 0 0;
        color: #94A3B8;
        font-size: 0.9rem;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(6, 78, 59, 0.45);
        color: #34D399;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(52, 211, 153, 0.35);
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.15);
    }
    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
    }

    /* KPI Metric Cards Ribbon */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.1rem 1.35rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(129, 140, 248, 0.4);
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.4rem;
        font-weight: 800;
        color: #F8FAFC;
    }

    /* Night Mode Proactive Insight Card */
    .insight-card {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%);
        border: 1px solid rgba(129, 140, 248, 0.35);
        border-left: 4px solid #818CF8;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin: 0.85rem 0;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), 0 0 16px rgba(99, 102, 241, 0.1);
    }
    .insight-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.825rem;
        font-weight: 700;
        color: #A5B4FC;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .insight-text {
        font-size: 1.05rem;
        line-height: 1.65;
        color: #F8FAFC !important;
        font-weight: 500;
        margin: 0;
    }
    .insight-text strong {
        color: #FFFFFF !important;
        font-weight: 700;
    }

    /* Night Mode User Message Bubble */
    .user-bubble {
        background: #1E293B;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #818CF8;
        border-radius: 12px;
        padding: 0.9rem 1.25rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: #F8FAFC !important;
        margin-bottom: 0.5rem;
    }

    /* Sidebar Night Mode Polish */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.05em;
        margin: 1.25rem 0 0.5rem 0;
    }
    .dataset-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: #1E293B;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #E2E8F0;
    }
    .dataset-badge {
        background: rgba(99, 102, 241, 0.2);
        color: #A5B4FC;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }

    /* High-Contrast Interactive Buttons */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background: #1E293B !important;
        color: #F1F5F9 !important;
    }
    div.stButton > button:hover {
        border-color: #818CF8 !important;
        color: #FFFFFF !important;
        background: #2D3748 !important;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.25) !important;
        transform: translateY(-1px);
    }

    /* Chat input contrast */
    .stChatInputContainer {
        border-color: rgba(255, 255, 255, 0.15) !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if "db_conn" not in st.session_state:
    st.session_state.db_conn = sqlite3.connect(":memory:", check_same_thread=False)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "loaded_files" not in st.session_state:
    st.session_state.loaded_files = set()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### ⚡ QueryMorph Control")
    st.caption("Multi-format data ingestion, live exports & engine settings.")

    # 1. Dataset Ingestion
    st.markdown('<div class="sidebar-section-title">1. Data Sources</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Drop CSV, Excel, or JSON files",
        type=["csv", "xlsx", "xls", "json"],
        accept_multiple_files=True,
        help="Files are automatically loaded into relational tables for natural language querying."
    )

    if uploaded_files:
        for file_obj in uploaded_files:
            if file_obj.name not in st.session_state.loaded_files:
                try:
                    dfs = load_file_to_dataframes(file_obj, filename=file_obj.name)
                    save_dataframes_to_sqlite(dfs, st.session_state.db_conn)
                    st.session_state.loaded_files.add(file_obj.name)
                    st.toast(f"Loaded: {', '.join(dfs.keys())}", icon="✅")
                except Exception as e:
                    st.error(f"Error loading {file_obj.name}: {e}")

    # Active Datasets Listing
    schema_dict, ddl_text, sample_data = get_database_schema(st.session_state.db_conn)
    current_tables = list(schema_dict.keys())

    if current_tables:
        st.markdown('<div class="sidebar-section-title">Active Datasets</div>', unsafe_allow_html=True)
        total_rows_all = 0
        for tbl in current_tables:
            cursor = st.session_state.db_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM '{tbl}'")
            count = cursor.fetchone()[0]
            total_rows_all += count
            st.markdown(
                f'<div class="dataset-item"><span>📁 {tbl.replace("_", " ").title()}</span><span class="dataset-badge">{count} rows</span></div>',
                unsafe_allow_html=True
            )
    else:
        total_rows_all = 0
        st.info("No datasets loaded yet. Upload files above or load the starter pack.")

    # 2. Data Export
    if current_tables:
        st.markdown('<div class="sidebar-section-title">2. Export Data</div>', unsafe_allow_html=True)
        export_tbl = st.selectbox("Select table", current_tables, label_visibility="collapsed")
        export_fmt = st.selectbox("Format", ["CSV", "Excel", "JSON"])

        if st.button("⬇️ Download Exported Dataset", use_container_width=True):
            try:
                data_bytes = export_table(st.session_state.db_conn, export_tbl, export_fmt.lower())
                mime_map = {
                    "CSV": "text/csv",
                    "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "JSON": "application/json"
                }
                ext_map = {"CSV": "csv", "Excel": "xlsx", "JSON": "json"}
                
                st.download_button(
                    label=f"Save {export_tbl}.{ext_map[export_fmt]}",
                    data=data_bytes,
                    file_name=f"{export_tbl}_data.{ext_map[export_fmt]}",
                    mime=mime_map[export_fmt],
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Export failed: {e}")

    # 3. Model Engine Preferences (Cleanly contained in expander)
    st.markdown('<div class="sidebar-section-title">3. Intelligence Engine</div>', unsafe_allow_html=True)
    with st.expander("Configure AI Engine", expanded=False):
        provider_choice = st.radio(
            "AI Provider",
            ["Groq (Fast / GPT-OSS)", "Gemini (Google GenAI)"],
            index=0
        )
        provider = "groq" if "Groq" in provider_choice else "gemini"

        if provider == "groq":
            groq_key = st.text_input("Groq Key", value=DEFAULT_GROQ_KEY, type="password")
            model_name = st.selectbox("Model", ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b"], index=0)
            api_key = groq_key
        else:
            gemini_key = st.text_input("Gemini Key", value=DEFAULT_GEMINI_KEY, type="password")
            model_name = st.selectbox("Model", ["gemini-3.5-flash-lite", "gemini-3.8-flash"], index=0)
            api_key = gemini_key

    # Initialize SQL Agent
    try:
        agent = SQLAgent(provider=provider, api_key=api_key, model_name=model_name)
    except Exception as e:
        st.error(f"Engine initialization error: {e}")
        agent = None

# ----------------- MAIN VIEW -----------------
# Header Ribbon
st.markdown(f"""
<div class="studio-header">
    <div>
        <h1 class="studio-title">⚡ QueryMorph Studio</h1>
        <p class="studio-subtitle">The Universal Conversational Data Engine &mdash; Ingest multi-format files, run self-healing SQL, and manage CRUD in natural language.</p>
    </div>
    <div class="status-badge">
        <div class="status-dot"></div>
        <span>{provider.upper()} Connected (Night Mode)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Executive Metric Ribbon
if current_tables:
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">Active Datasets</div>
            <div class="metric-val">{len(current_tables)} Tables</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Records</div>
            <div class="metric-val">{total_rows_all:,}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Inference Engine</div>
            <div class="metric-val">{model_name.split('/')[-1]}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Operation Scope</div>
            <div class="metric-val">Query & CRUD</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Empty State with Starter Pack Button
    st.info("👋 **Welcome to the Studio!** Upload your CSV, Excel, or JSON files in the sidebar, or initialize with our multi-source starter portfolio:")
    if st.button("📂 Load Starter Portfolio (Universities CSV + Students JSON + Courses Excel)", type="primary"):
        from app import load_all_sample_files
        loaded = load_all_sample_files(st.session_state.db_conn)
        st.success(f"Starter portfolio loaded: {', '.join(loaded)}")
        st.rerun()

# Dataset Intelligence & Proactive Suggestions
if current_tables and agent:
    if "dataset_brief" not in st.session_state or st.session_state.get("brief_count") != len(current_tables):
        with st.spinner("Analyzing data patterns & relationships..."):
            st.session_state.dataset_brief = agent.get_dataset_brief(st.session_state.db_conn)
            st.session_state.brief_count = len(current_tables)

    if st.session_state.get("dataset_brief"):
        brief = st.session_state.dataset_brief
        sugg_questions = brief.get("suggested_questions", [])
        if sugg_questions:
            st.caption("✨ **PROACTIVE DATA EXPLORATION (CLICK TO RUN)**")
            cols = st.columns(min(len(sugg_questions), 3))
            for idx, q in enumerate(sugg_questions[:3]):
                with cols[idx]:
                    if st.button(f"🔍 {q}", key=f"sugg_{idx}", use_container_width=True):
                        st.session_state.pending_prompt = q
                        st.rerun()

# Dataset Preview Tabs (Compact)
if current_tables:
    with st.expander("👁️ Inspect Live Datasets", expanded=False):
        tabs = st.tabs([t.replace('_', ' ').title() for t in current_tables])
        for i, tbl in enumerate(current_tables):
            with tabs[i]:
                preview_df = pd.read_sql_query(f"SELECT * FROM '{tbl}' LIMIT 50", st.session_state.db_conn)
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ----------------- CHAT STREAM -----------------
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            # ONLY PROACTIVE INSIGHT
            insight_content = message.get("insight", message.get("content", ""))
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-header">
                    <span>💡 Proactive Data Insight</span>
                </div>
                <div class="insight-text">
                    {insight_content}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Tabular data if returned
            if message.get("data") is not None and not message["data"].empty:
                st.dataframe(message["data"], use_container_width=True, hide_index=True)

            # Clean micro-drawer for technical specs
            if message.get("sql"):
                with st.expander("Technical Query Specs", expanded=False):
                    st.code(message["sql"], language="sql")
                    st.caption(f"Operation: `{message.get('op_type', 'QUERY')}`")

# ----------------- PROMPT INPUT -----------------
typed_prompt = st.chat_input("Ask a strategic question or request a database modification...")
user_prompt = None

if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
elif typed_prompt:
    user_prompt = typed_prompt

if user_prompt:
    # Render user prompt
    st.chat_message("user").markdown(f'<div class="user-bubble">{user_prompt}</div>', unsafe_allow_html=True)
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        if not agent:
            st.error("Intelligence engine is not configured.")
        else:
            with st.spinner("Analyzing database & synthesizing proactive insights..."):
                schema_dict, ddl_text, sample_data = get_database_schema(st.session_state.db_conn)
                
                result = agent.process_nl_request(
                    conn=st.session_state.db_conn,
                    user_prompt=user_prompt,
                    schema_dict=schema_dict,
                    ddl_schema=ddl_text,
                    sample_data=sample_data
                )

                if result["success"]:
                    # Solely the proactive insight
                    insight_text = result.get("human_response", "Insight synthesized successfully.")
                    st.markdown(f"""
                    <div class="insight-card">
                        <div class="insight-header">
                            <span>💡 Proactive Data Insight</span>
                        </div>
                        <div class="insight-text">
                            {insight_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Display clean table if data returned
                    if result["data"] is not None and not result["data"].empty:
                        st.dataframe(result["data"], use_container_width=True, hide_index=True)

                    # Optional technical drawer
                    with st.expander("Technical Query Specs", expanded=False):
                        st.code(result["sql"], language="sql")
                        st.caption(f"Operation: `{result['op_type']}` | Impact: {result.get('rows_affected', 0)} records")

                    # Append to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "insight": insight_text,
                        "data": result["data"],
                        "sql": result["sql"],
                        "op_type": result["op_type"]
                    })
                else:
                    error_msg = result.get("human_response", f"Unable to process request: {result.get('error')}")
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "insight": error_msg,
                        "data": None,
                        "sql": result.get("sql", ""),
                        "op_type": "ERROR"
                    })
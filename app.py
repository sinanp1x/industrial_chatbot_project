import os
import streamlit as st
import pandas as pd
from core.vector_store import LocalVectorStore
from core.doc_loader import DocumentLoader
from core.log_parser import LogParser
from core.hf_client import get_hf_client
from agent.graph import build_industrial_graph
from langchain_core.messages import HumanMessage, AIMessage

# --- Configuration & Styling ---
st.set_page_config(page_title="Chatbot | Industrial Copilot", page_icon="🏭", layout="wide")

# Custom CSS for Industrial Theme
st.markdown("""
<style>
    /* Industrial Palette */
    :root {
      --bg-industrial: #0e1117;
      --surface-card: #1a1f2c;
      --border-subtle: #2d3748;
      --accent-blue: #3182ce;
      --safety-amber: #d69e2e;
      --emergency-red: #e53e3e;
      --text-primary: #f7fafc;
    }
    .safety-alert {
      background-color: rgba(229, 62, 62, 0.15);
      border-left: 4px solid #e53e3e;
      padding: 12px 16px;
      border-radius: 4px;
      margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = LocalVectorStore()
if 'doc_loader' not in st.session_state:
    st.session_state.doc_loader = DocumentLoader()
if 'log_parser' not in st.session_state:
    st.session_state.log_parser = LogParser()
if 'active_logs_content' not in st.session_state:
    st.session_state.active_logs_content = None
if 'active_log_filename' not in st.session_state:
    st.session_state.active_log_filename = "log"
if 'parsed_logs' not in st.session_state:
    st.session_state.parsed_logs = None
if 'indexed_docs_meta' not in st.session_state:
    st.session_state.indexed_docs_meta = []
# Track uploaded file identities to detect changes across rerenders
if '_last_log_key' not in st.session_state:
    st.session_state._last_log_key = None
if '_last_manuals_key' not in st.session_state:
    st.session_state._last_manuals_key = None


# --- Main Viewport ---
st.title("🏭 Chatbot | Industrial Copilot & Equipment Diagnostics")

# --- Data Ingestion Panel ---
with st.expander("📂 Data Ingestion (Upload Manuals & Telemetry Logs)", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📚 Knowledge Base")
        uploaded_manuals = st.file_uploader(
            "Upload Manuals & SOPs", type=["pdf", "txt"], accept_multiple_files=True
        )

        if uploaded_manuals:
            # Auto-index when a new set of files is detected (identity = sorted name+size tuple)
            manuals_key = tuple(sorted((f.name, len(f.getvalue())) for f in uploaded_manuals))
            if manuals_key != st.session_state._last_manuals_key:
                with st.spinner("Extracting and Indexing..."):
                    st.session_state.vector_store.clear()
                    # Capture metadata BEFORE load_and_split reads the files
                    meta = [{"filename": f.name, "size": len(f.getvalue())} for f in uploaded_manuals]
                    chunks = st.session_state.doc_loader.load_and_split(uploaded_manuals)
                    st.session_state.vector_store.add_documents(chunks)
                    st.session_state.indexed_docs_meta = meta
                    st.session_state._last_manuals_key = manuals_key
                st.success(f"✅ Auto-indexed {len(chunks)} chunks from {len(uploaded_manuals)} file(s).")

            # Manual re-index button (force refresh)
            if st.button("🔄 Force Re-index"):
                with st.spinner("Re-indexing..."):
                    st.session_state.vector_store.clear()
                    meta = [{"filename": f.name, "size": len(f.getvalue())} for f in uploaded_manuals]
                    chunks = st.session_state.doc_loader.load_and_split(uploaded_manuals)
                    st.session_state.vector_store.add_documents(chunks)
                    st.session_state.indexed_docs_meta = meta
                    st.session_state._last_manuals_key = manuals_key
                st.success(f"✅ Re-indexed {len(chunks)} chunks from {len(uploaded_manuals)} file(s).")

    with col2:
        st.subheader("⚡ Active Telemetry")
        uploaded_log = st.file_uploader("Upload Shift Logs / Fault Data", type=["txt", "log", "csv"])
        if uploaded_log:
            # Auto-parse when a new log file is detected (identity = name + size)
            log_key = (uploaded_log.name, uploaded_log.size)
            if log_key != st.session_state._last_log_key:
                content = uploaded_log.getvalue().decode("utf-8", errors="replace")
                st.session_state.active_logs_content = content
                st.session_state.active_log_filename = uploaded_log.name
                st.session_state.parsed_logs = st.session_state.log_parser.parse_log(
                    content, source_filename=uploaded_log.name
                )
                st.session_state._last_log_key = log_key
                st.success(f"✅ Log '{uploaded_log.name}' parsed automatically.")
            else:
                st.info("Log already parsed. Upload a new file to refresh.")
                
    with col3:
        st.subheader("🚀 Quick Start")
        st.markdown("Don't have files? Load the built-in sample data to test the chatbot immediately.")
        if st.button("Load Sample Data"):
            with st.spinner("Loading sample data..."):
                # Load sample manual
                manual_path = "samples/sample_manual_press_line.txt"
                if os.path.exists(manual_path):
                    st.session_state.vector_store.clear()
                    with open(manual_path, "r", encoding="utf-8") as f:
                        manual_content = f.read()
                    
                    # Create a mock file object for doc loader
                    class MockFile:
                        def __init__(self, name, content):
                            self.name = name
                            self.content = content.encode("utf-8")
                        def getvalue(self):
                            return self.content
                            
                    mock_file = MockFile("sample_manual_press_line.txt", manual_content)
                    chunks = st.session_state.doc_loader.load_and_split([mock_file])
                    st.session_state.vector_store.add_documents(chunks)
                    st.session_state.indexed_docs_meta = [{"filename": mock_file.name, "size": len(mock_file.getvalue())}]
                
                # Load sample logs
                log_path = "samples/sample_shift_telemetry.log"
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8") as f:
                        log_content = f.read()
                    sample_log_name = "sample_shift_telemetry.log"
                    st.session_state.active_logs_content = log_content
                    st.session_state.active_log_filename = sample_log_name
                    st.session_state.parsed_logs = st.session_state.log_parser.parse_log(
                        log_content, source_filename=sample_log_name
                    )

                # Reset file identity trackers so real uploads are re-detected properly
                st.session_state._last_log_key = None
                st.session_state._last_manuals_key = None
                st.success("Sample data loaded! You can now ask questions in the chat.")


# --- Status Bar ---
status_cols = st.columns(2)
if st.session_state.indexed_docs_meta:
    status_cols[0].markdown(f"**🟢 Knowledge Base:** {len(st.session_state.indexed_docs_meta)} Documents Indexed")
else:
    status_cols[0].markdown("**⚪ Knowledge Base:** Empty")

if st.session_state.parsed_logs:
    errors = st.session_state.parsed_logs["counts"].get("ERROR", 0) + st.session_state.parsed_logs["counts"].get("FATAL", 0)
    if errors > 0:
        status_cols[1].markdown(f"**🔴 Telemetry:** {errors} Critical Errors Detected")
    else:
        status_cols[1].markdown("**🟢 Telemetry:** Clean Log")
else:
    status_cols[1].markdown("**⚪ Telemetry:** No logs loaded")

st.divider()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["💬 Diagnostic Chat", "📊 Log Anomaly Table", "📚 Manuals Knowledge Base"])

with tab1:
    # Display chat history
    for msg in st.session_state.chat_history:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(msg.content)
                if hasattr(msg, 'sources') and msg.sources:
                    with st.expander("📖 Cited Manual Excerpts"):
                        for source in msg.sources:
                            st.markdown(f"- **{source['source']}** — Page {source['page']}")
                if hasattr(msg, 'log_citations') and msg.log_citations:
                    with st.expander("📋 Referenced Log Lines"):
                        for cite in msg.log_citations:
                            badge = {"FATAL": "🔴", "ERROR": "🟠", "WARN": "🟡"}.get(cite["level"], "⚪")
                            st.markdown(
                                f"{badge} **{cite['source']}:L{cite['line']}** "
                                f"— `{cite['timestamp']}` [{cite['level']}]"
                            )
    
    # Pre-canned prompts
    col1, col2, col3, col4 = st.columns(4)
    pre_prompt = None
    if col1.button("🔍 Diagnose all errors in the uploaded log"):
        pre_prompt = "Diagnose all errors in the uploaded log."
    if col2.button("📖 What are the weekly maintenance steps for Motor M1?"):
        pre_prompt = "What are the weekly maintenance steps for Motor M1?"
    if col3.button("⚠️ List safety precautions and LOTO procedure for line stoppage"):
         pre_prompt = "List safety precautions and LOTO procedure for line stoppage."
    if col4.button("🔧 Explain fault code ERR_HYD_OVERPRESS and give remedy"):
         pre_prompt = "Explain fault code ERR_HYD_OVERPRESS and give remedy."
         
    user_input = st.chat_input("Ask about equipment specs, manual rules, or diagnose current log...")
    query = pre_prompt if pre_prompt else user_input

    if query:
        # Display user input
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.chat_history.append(HumanMessage(content=query))
        
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # We no longer strictly require hf_token to be passed if we rely on the environment
                    llm_client = get_hf_client()
                    graph = build_industrial_graph(st.session_state.vector_store, st.session_state.log_parser, llm_client)
                    
                    initial_state = {
                        "query": query,
                        "chat_history": st.session_state.chat_history,
                        "active_logs": st.session_state.active_logs_content,
                        "log_filename": st.session_state.get("active_log_filename", "log"),
                        "has_logs": st.session_state.active_logs_content is not None,
                        "has_manuals": len(st.session_state.indexed_docs_meta) > 0,
                        # initialise citation lists so state is always well-formed
                        "log_citations": [],
                        "extracted_faults": [],
                        "log_summary": "",
                        "retrieved_manual_chunks": [],
                        "sources": [],
                    }
                    
                    result_state = graph.invoke(initial_state)
                    final_response = result_state.get("final_response", "No response generated.")
                    sources = result_state.get("sources", [])
                    log_citations = result_state.get("log_citations", [])

                    st.markdown(final_response)

                    # Show manual citations
                    if sources:
                        with st.expander("📖 Cited Manual Excerpts"):
                            for src in sources:
                                st.markdown(f"- **{src['source']}** — Page {src['page']}")

                    # Show log line citations
                    if log_citations:
                        with st.expander("📋 Referenced Log Lines"):
                            for cite in log_citations:
                                badge = {
                                    "FATAL": "🔴", "ERROR": "🟠", "WARN": "🟡"
                                }.get(cite["level"], "⚪")
                                st.markdown(
                                    f"{badge} **{cite['source']}:L{cite['line']}** "
                                    f"— `{cite['timestamp']}` [{cite['level']}]"
                                )

                    ai_msg = AIMessage(content=final_response)
                    ai_msg.sources = sources
                    ai_msg.log_citations = log_citations
                    st.session_state.chat_history.append(ai_msg)
                    
                except Exception as e:
                    st.error(f"An error occurred while communicating with the model: {e}")

with tab2:
    st.subheader("Telemetry Inspector")
    if st.session_state.parsed_logs:
        counts = st.session_state.parsed_logs["counts"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Lines", len(st.session_state.parsed_logs["entries"]))
        c2.metric("Warnings", counts.get("WARN", 0))
        c3.metric("Errors/Fatal", counts.get("ERROR", 0) + counts.get("FATAL", 0), delta_color="inverse")
        c4.metric("Unique Faults", len(st.session_state.parsed_logs["unique_faults"]))
        
        # Log Table
        anomalies = st.session_state.parsed_logs["anomalies"]
        if anomalies:
            df = pd.DataFrame(anomalies)
            # Reorder/rename columns for display
            df = df[["timestamp", "level", "subsystem", "message", "fault_codes"]]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No critical anomalies found in logs.")
            
        with st.expander("Raw Log Content"):
            st.text(st.session_state.active_logs_content)
    else:
        st.info("Upload and parse logs in the Data Ingestion panel to view telemetry.")

with tab3:
    st.subheader("Indexed Documents")
    if st.session_state.indexed_docs_meta:
        df_docs = pd.DataFrame(st.session_state.indexed_docs_meta)
        st.dataframe(df_docs, use_container_width=True)
        
        st.subheader("Search Sandbox")
        test_query = st.text_input("Test Vector Search:")
        if test_query:
            results = st.session_state.vector_store.search(test_query, k=3)
            for res in results:
                st.markdown(f"**Source**: {res.metadata.get('source_file')} (Page {res.metadata.get('page')})")
                st.text(res.page_content)
    else:
         st.info("Upload manuals in the Data Ingestion panel to populate the Knowledge Base.")

import streamlit as st
import pandas as pd
from core.vector_store import LocalVectorStore
from core.doc_loader import DocumentLoader
from core.log_parser import LogParser
from core.openrouter_client import get_openrouter_client
from agent.graph import build_industrial_graph
from langchain_core.messages import HumanMessage, AIMessage

# --- Configuration & Styling ---
st.set_page_config(page_title="RoboAI | Industrial Copilot", page_icon="🏭", layout="wide")

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
if 'parsed_logs' not in st.session_state:
    st.session_state.parsed_logs = None
if 'indexed_docs_meta' not in st.session_state:
    # Just to track what files have been uploaded (could be inferred from vector_store but this is easier for UI)
    st.session_state.indexed_docs_meta = []


# --- Sidebar ---
st.sidebar.title("⚙️ Configuration")
api_key = st.sidebar.text_input("OpenRouter API Key", type="password")
if api_key:
    st.session_state.api_key = api_key
    
model_selector = st.sidebar.selectbox(
    "Model Selector",
    options=["anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini", "meta-llama/llama-3.1-8b-instruct", "deepseek/deepseek-chat"]
)

st.sidebar.divider()

# Knowledge Base Dock
st.sidebar.subheader("📚 Knowledge Base (Manuals)")
uploaded_manuals = st.sidebar.file_uploader("Upload Manuals & SOPs", type=["pdf", "txt"], accept_multiple_files=True)

if st.sidebar.button("Re-index All") and uploaded_manuals:
    with st.spinner("Extracting and Indexing..."):
        st.session_state.vector_store.clear()
        chunks = st.session_state.doc_loader.load_and_split(uploaded_manuals)
        st.session_state.vector_store.add_documents(chunks)
        
        # Update metadata for UI
        st.session_state.indexed_docs_meta = []
        for file in uploaded_manuals:
            st.session_state.indexed_docs_meta.append({"filename": file.name, "size": len(file.getvalue())})
            
        st.sidebar.success(f"Indexed {len(chunks)} chunks from {len(uploaded_manuals)} files.")

if st.session_state.indexed_docs_meta:
    st.sidebar.markdown(f"**🟢 Index Ready** ({len(st.session_state.indexed_docs_meta)} Documents)")
    for doc in st.session_state.indexed_docs_meta:
        st.sidebar.markdown(f"- {doc['filename']}")
else:
    st.sidebar.markdown("⚪ No manuals loaded")
    
if st.sidebar.button("Clear Knowledge Base"):
    st.session_state.vector_store.clear()
    st.session_state.indexed_docs_meta = []
    st.sidebar.info("Knowledge Base cleared.")


st.sidebar.divider()

# Telemetry Dock
st.sidebar.subheader("⚡ Active Telemetry / Logs")
uploaded_log = st.sidebar.file_uploader("Upload Shift Logs / Fault Data", type=["txt", "log", "csv"])

if uploaded_log:
    if st.sidebar.button("Parse Logs"):
        content = uploaded_log.getvalue().decode("utf-8")
        st.session_state.active_logs_content = content
        st.session_state.parsed_logs = st.session_state.log_parser.parse_log(content)
        
if st.session_state.parsed_logs:
    errors = st.session_state.parsed_logs["counts"].get("ERROR", 0) + st.session_state.parsed_logs["counts"].get("FATAL", 0)
    warnings = st.session_state.parsed_logs["counts"].get("WARN", 0)
    if errors > 0:
        st.sidebar.markdown(f"**🔴 {errors} Critical Errors Detected**")
    elif warnings > 0:
         st.sidebar.markdown(f"**🟡 {warnings} Warnings**")
    else:
         st.sidebar.markdown("**🟢 Clean Log**")
         
    faults = st.session_state.parsed_logs["unique_faults"]
    if faults:
        st.sidebar.markdown(f"**Top Faults**: {', '.join(faults)}")
        
if st.sidebar.button("Flush Active Log"):
    st.session_state.active_logs_content = None
    st.session_state.parsed_logs = None


# --- Main Viewport ---
st.title("🏭 RoboAI | Industrial Copilot & Equipment Diagnostics")

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
                            st.markdown(f"- **{source['source']}** (Page {source['page']})")
    
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
        
        # Check API key before proceeding
        api_key_to_use = st.session_state.get('api_key', os.environ.get("OPENROUTER_API_KEY"))
        if not api_key_to_use:
             with st.chat_message("assistant"):
                 st.error("Please provide an OpenRouter API Key in the sidebar or via the .env file.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    try:
                        llm_client = get_openrouter_client(model_name=model_selector, api_key=api_key_to_use)
                        graph = build_industrial_graph(st.session_state.vector_store, st.session_state.log_parser, llm_client)
                        
                        initial_state = {
                            "query": query,
                            "chat_history": st.session_state.chat_history,
                            "active_logs": st.session_state.active_logs_content,
                            "has_logs": st.session_state.active_logs_content is not None,
                            "has_manuals": len(st.session_state.indexed_docs_meta) > 0,
                        }
                        
                        result_state = graph.invoke(initial_state)
                        final_response = result_state.get("final_response", "No response generated.")
                        sources = result_state.get("sources", [])
                        
                        st.markdown(final_response)
                        
                        # Show sources
                        if sources:
                            with st.expander("📖 Cited Manual Excerpts"):
                                for source in sources:
                                    st.markdown(f"- **{source['source']}** (Page {source['page']})")
                                    
                        ai_msg = AIMessage(content=final_response)
                        ai_msg.sources = sources
                        st.session_state.chat_history.append(ai_msg)
                        
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

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
        st.info("Upload and parse logs in the sidebar to view telemetry.")

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
         st.info("Upload manuals in the sidebar to populate the Knowledge Base.")

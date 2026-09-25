from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import IndustrialAgentState

# Max recent chat turns to include in the prompt (to stay within token budget)
MAX_HISTORY_TURNS = 6


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

def classify_intent_node(state: IndustrialAgentState) -> IndustrialAgentState:
    """
    Routes the query to the most appropriate retrieval path.

    Priority:
      1. log_troubleshoot  — any fault/diagnostic query when logs are loaded
      2. doc_qa            — documentation / procedure / spec lookup
      3. general           — everything else (may still use both sources)
    """
    query = state.get("query", "").lower()
    has_logs = state.get("has_logs", False)
    has_manuals = state.get("has_manuals", False)

    # --- Log troubleshooting signals ---
    log_keywords = [
        "error", "fault", "log", "alarm", "trip", "shutdown", "halt",
        "diagnose", "diagnose", "why", "what happened", "what went wrong",
        "failure", "failed", "warning", "anomaly", "overpress", "overheat",
        "critical", "crash", "status", "problem", "issue", "code",
    ]

    # --- Documentation / knowledge-base signals ---
    doc_keywords = [
        "spec", "specification", "wiring", "parameter", "maintenance",
        "sop", "procedure", "steps", "manual", "guide", "how to",
        "what is", "torque", "pressure rating", "calibrate", "install",
        "configure", "rule", "standard", "requirement",
    ]

    if has_logs and any(kw in query for kw in log_keywords):
        intent = "log_troubleshoot"
    elif has_manuals and any(kw in query for kw in doc_keywords):
        intent = "doc_qa"
    else:
        intent = "general"

    return {"intent": intent}


# ---------------------------------------------------------------------------
# Retrieval — Knowledge Base (manuals / SOPs)
# ---------------------------------------------------------------------------

def retrieve_knowledge_node(state: IndustrialAgentState, vector_store) -> IndustrialAgentState:
    """
    Retrieve grounding information from uploaded equipment manuals (PDF/TXT) via FAISS.
    Also includes log context if logs are present, so the LLM has full picture.
    """
    log_summary = state.get("log_summary", "No logs provided.")
    log_citations: List[Dict[str, Any]] = state.get("log_citations", [])

    if not state.get("has_manuals", False):
        return {
            "retrieved_manual_chunks": ["No equipment manuals currently indexed."],
            "sources": [],
            "log_summary": log_summary,
            "log_citations": log_citations,
        }

    query = state.get("query", "")
    results = vector_store.search(query, k=5)

    chunks = []
    sources = []
    for doc in results:
        chunks.append(doc.page_content)
        sources.append({
            "source": doc.metadata.get("source_file", "Unknown"),
            "page": doc.metadata.get("page", 0),
            "chunk_id": doc.metadata.get("chunk_id", ""),
        })

    return {
        "retrieved_manual_chunks": chunks,
        "sources": sources,
        "log_summary": log_summary,
        "log_citations": log_citations,
    }


# ---------------------------------------------------------------------------
# Retrieval — Log Analysis (cross-referenced with manuals)
# ---------------------------------------------------------------------------

def analyze_logs_node(state: IndustrialAgentState, vector_store, log_parser) -> IndustrialAgentState:
    """
    Parse the uploaded log file, extract faults, and cross-reference with manuals.
    Every anomalous log line is tagged with a citation [filename:L<n>] for the LLM.
    """
    if not state.get("has_logs", False) or not state.get("active_logs"):
        return {
            "extracted_faults": [],
            "log_summary": "No active logs available.",
            "log_citations": [],
            "retrieved_manual_chunks": ["Cannot perform log analysis without logs."],
            "sources": [],
        }

    log_filename = state.get("log_filename", "log")
    parsed_data = log_parser.parse_log(state["active_logs"], source_filename=log_filename)

    faults = parsed_data["unique_faults"]
    summary = parsed_data["summary_text"]
    log_citations = parsed_data["log_citations"]

    chunks: List[str] = []
    sources: List[Dict[str, Any]] = []

    if state.get("has_manuals", False):
        if faults:
            # Query FAISS for each detected fault to find remediation steps
            seen_chunks = set()
            for fault in faults:
                search_query = f"Troubleshooting procedure remedy for fault {fault}"
                results = vector_store.search(search_query, k=2)
                for doc in results:
                    cid = doc.metadata.get("chunk_id", doc.page_content[:40])
                    if cid not in seen_chunks:
                        seen_chunks.add(cid)
                        chunks.append(doc.page_content)
                        sources.append({
                            "source": doc.metadata.get("source_file", "Unknown"),
                            "page": doc.metadata.get("page", 0),
                            "chunk_id": doc.metadata.get("chunk_id", ""),
                        })
        else:
            # No specific fault codes — use the raw query to retrieve relevant manual sections
            results = vector_store.search(state.get("query", ""), k=4)
            for doc in results:
                chunks.append(doc.page_content)
                sources.append({
                    "source": doc.metadata.get("source_file", "Unknown"),
                    "page": doc.metadata.get("page", 0),
                    "chunk_id": doc.metadata.get("chunk_id", ""),
                })

    return {
        "extracted_faults": faults,
        "log_summary": summary,
        "log_citations": log_citations,
        "retrieved_manual_chunks": chunks,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# General Context — gather all available grounding material
# ---------------------------------------------------------------------------

def general_context_node(state: IndustrialAgentState, vector_store, log_parser) -> IndustrialAgentState:
    """
    For general queries: gather ALL available context — manual chunks (if any) and
    log summary with citations (if any).  Prevents the LLM from answering with zero grounding.
    """
    query = state.get("query", "")
    chunks: List[str] = []
    sources: List[Dict[str, Any]] = []
    log_summary = "No logs provided."
    log_citations: List[Dict[str, Any]] = []

    # Retrieve relevant manual excerpts if knowledge base is populated
    if state.get("has_manuals", False):
        results = vector_store.search(query, k=4)
        for doc in results:
            chunks.append(doc.page_content)
            sources.append({
                "source": doc.metadata.get("source_file", "Unknown"),
                "page": doc.metadata.get("page", 0),
                "chunk_id": doc.metadata.get("chunk_id", ""),
            })

    # Include log summary & citations if logs are loaded
    if state.get("has_logs", False) and state.get("active_logs"):
        log_filename = state.get("log_filename", "log")
        parsed_data = log_parser.parse_log(state["active_logs"], source_filename=log_filename)
        log_summary = parsed_data["summary_text"]
        log_citations = parsed_data["log_citations"]

    return {
        "retrieved_manual_chunks": chunks,
        "sources": sources,
        "log_summary": log_summary,
        "log_citations": log_citations,
        "extracted_faults": [],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_chat_history(chat_history: list) -> str:
    """Formats the last N turns of chat history for the prompt."""
    if not chat_history:
        return ""
    recent = chat_history[-(MAX_HISTORY_TURNS + 1):-1]
    lines = []
    for msg in recent:
        if isinstance(msg, HumanMessage):
            lines.append(f"Operator: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")
    return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Response Synthesis
# ---------------------------------------------------------------------------

def synthesize_response_node(state: IndustrialAgentState, llm_client) -> IndustrialAgentState:
    """
    Build the final, grounded LLM response from all gathered context.
    """
    query            = state.get("query", "")
    intent           = state.get("intent", "general")
    log_summary      = state.get("log_summary", "No logs provided.")
    manual_chunks    = state.get("retrieved_manual_chunks", [])
    extracted_faults = state.get("extracted_faults", [])
    log_citations    = state.get("log_citations", [])
    chat_history     = state.get("chat_history", [])
    has_logs         = state.get("has_logs", False)
    has_manuals      = state.get("has_manuals", False)

    # --- Assemble context blocks ---
    manual_text = (
        "\n\n---\n\n".join(manual_chunks)
        if manual_chunks
        else "No manual excerpts available."
    )

    faults_text = (
        "Detected fault codes: " + ", ".join(extracted_faults)
        if extracted_faults
        else ""
    )

    history_text  = _format_chat_history(chat_history)
    history_block = (
        f"\n--- CONVERSATION HISTORY ---\n{history_text}\n--- END HISTORY ---\n"
        if history_text
        else ""
    )

    # --- Context availability hints ---
    ctx_hints = []
    if not has_logs:
        ctx_hints.append("No log file has been uploaded for this session.")
    if not has_manuals:
        ctx_hints.append("No equipment manuals are indexed.")
    context_notes = ("\n".join(ctx_hints) + "\n") if ctx_hints else ""

    # --- Build the optimised system prompt ---
    prompt = f"""You are an Industrial Diagnostics Assistant — a precise, safety-focused expert \
in industrial equipment, PLC systems, hydraulics, electrical systems, and manufacturing operations.

CORE RULES:
• Base EVERY answer strictly on the provided context below. Never hallucinate specs, tolerances, \
voltages, or procedures that are not in the supplied context.
• If the required information is absent from the context, say clearly: \
"Specific information not found in the indexed materials. Contact OEM support or engineering."
• When referencing a log line, cite it as [filename:L<line_number>] — exactly as tagged in the \
LOG ANOMALIES block below.
• When referencing a manual, cite it as [filename, page N].
• SAFETY FIRST: If an action involves Lockout/Tagout (LOTO), arc flash, or high-voltage hazard, \
state it in bold at the very top of your answer before anything else.
• Adapt response depth to the question: simple questions get concise answers; fault diagnosis \
gets full structured analysis.
{context_notes}{history_block}
=== CONTEXT START ===

LOG DATA:
{log_summary}
{faults_text}

MANUAL EXCERPTS:
{manual_text}

=== CONTEXT END ===

OPERATOR QUESTION: {query}

RESPONSE GUIDELINES (adapt structure to the question type):
- For fault/error diagnosis: lead with Fault Summary → Root Cause → Corrective Actions → Safety Notes → Citations
- For procedure/spec questions: answer directly with steps or values → cite the source
- For general questions: answer concisely using available context → note what is not covered
- Always end with citations for any log lines or manual pages you referenced.
"""

    messages = [{"role": "user", "content": prompt}]

    try:
        response = llm_client.invoke(messages)
        final_answer = response.content
    except Exception as e:
        final_answer = (
            f"⚠️ Error communicating with the model: {str(e)}\n"
            "Please check your API key and network connection."
        )

    return {
        "final_response": final_answer,
        "log_citations": log_citations,
    }

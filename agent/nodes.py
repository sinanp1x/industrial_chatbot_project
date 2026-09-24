from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import IndustrialAgentState

# Max recent chat turns to include in the prompt (to stay within token budget)
MAX_HISTORY_TURNS = 6


def classify_intent_node(state: IndustrialAgentState) -> IndustrialAgentState:
    """
    Determines what the user needs without executing unnecessary vector searches.
    """
    query = state.get("query", "").lower()
    has_logs = state.get("has_logs", False)

    intent = "general"

    # 1. Check for log troubleshoot intent
    troubleshoot_keywords = ["error", "fault", "log", "stop", "alarm", "status", "diagnose", "why"]
    if has_logs and any(word in query for word in troubleshoot_keywords):
        intent = "log_troubleshoot"
    # 2. Check for doc QA intent
    else:
        doc_keywords = [
            "spec", "wiring", "parameter", "maintenance", "sop", "rule",
            "manual", "guide", "how to", "what is", "procedure", "steps",
        ]
        if any(word in query for word in doc_keywords):
            intent = "doc_qa"

    return {"intent": intent}


def retrieve_knowledge_node(state: IndustrialAgentState, vector_store) -> IndustrialAgentState:
    """
    Retrieve ground truth information from uploaded equipment manuals (PDF/TXT) via FAISS.
    """
    if not state.get("has_manuals", False):
        return {
            "retrieved_manual_chunks": ["No equipment manuals currently indexed."],
            "sources": [],
            "log_summary": state.get("log_summary", "No logs provided."),
        }

    query = state.get("query", "")
    results = vector_store.search(query, k=4)

    chunks = []
    sources = []
    for doc in results:
        chunks.append(doc.page_content)
        source_file = doc.metadata.get("source_file", "Unknown")
        page = doc.metadata.get("page", 0)
        sources.append({"source": source_file, "page": page})

    return {
        "retrieved_manual_chunks": chunks,
        "sources": sources,
        "log_summary": state.get("log_summary", "No logs provided."),
    }


def analyze_logs_node(state: IndustrialAgentState, vector_store, log_parser) -> IndustrialAgentState:
    """
    Cross-reference active operational logs with equipment manuals to diagnose root causes.
    """
    if not state.get("has_logs", False) or not state.get("active_logs"):
        return {
            "extracted_faults": [],
            "log_summary": "No active logs available.",
            "retrieved_manual_chunks": ["Cannot perform log analysis without logs."],
            "sources": [],
        }

    # Parse the logs
    parsed_data = log_parser.parse_log(state["active_logs"])
    faults = parsed_data["unique_faults"]
    summary = parsed_data["summary_text"]

    chunks = []
    sources = []

    if state.get("has_manuals", False) and faults:
        # Query FAISS for each fault code to find remediation steps
        for fault in faults:
            search_query = f"Troubleshooting procedure for {fault}"
            results = vector_store.search(search_query, k=2)
            for doc in results:
                chunks.append(doc.page_content)
                sources.append({
                    "source": doc.metadata.get("source_file", "Unknown"),
                    "page": doc.metadata.get("page", 0),
                })
    elif state.get("has_manuals", False):
        # No specific faults extracted — fall back to query-based retrieval
        results = vector_store.search(state.get("query", ""), k=3)
        for doc in results:
            chunks.append(doc.page_content)
            sources.append({
                "source": doc.metadata.get("source_file", "Unknown"),
                "page": doc.metadata.get("page", 0),
            })

    return {
        "extracted_faults": faults,
        "log_summary": summary,
        "retrieved_manual_chunks": chunks,
        "sources": sources,
    }


def general_context_node(state: IndustrialAgentState, vector_store, log_parser) -> IndustrialAgentState:
    """
    For general queries: gather ALL available context — manual chunks (if any) and log
    summary (if any). Prevents the LLM from answering with zero grounding.
    """
    query = state.get("query", "")
    chunks: List[str] = []
    sources: List[Dict[str, Any]] = []
    log_summary = "No logs provided."

    # Retrieve relevant manual excerpts if knowledge base is populated
    if state.get("has_manuals", False):
        results = vector_store.search(query, k=4)
        for doc in results:
            chunks.append(doc.page_content)
            sources.append({
                "source": doc.metadata.get("source_file", "Unknown"),
                "page": doc.metadata.get("page", 0),
            })

    # Include log summary if logs are loaded
    if state.get("has_logs", False) and state.get("active_logs"):
        parsed_data = log_parser.parse_log(state["active_logs"])
        log_summary = parsed_data["summary_text"]

    return {
        "retrieved_manual_chunks": chunks,
        "sources": sources,
        "log_summary": log_summary,
        "extracted_faults": [],
    }


def _format_chat_history(chat_history: list) -> str:
    """
    Formats the last N turns of chat history into a human-readable string for the prompt.
    Only includes HumanMessage / AIMessage pairs.
    """
    if not chat_history:
        return ""

    # Take the last MAX_HISTORY_TURNS messages (exclude the current query which is the last HumanMessage)
    recent = chat_history[-(MAX_HISTORY_TURNS + 1):-1]  # exclude the current query already added

    lines = []
    for msg in recent:
        if isinstance(msg, HumanMessage):
            lines.append(f"Operator: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")

    return "\n".join(lines) if lines else ""


def synthesize_response_node(state: IndustrialAgentState, llm_client) -> IndustrialAgentState:
    """
    Assemble the final grounded response using the LLM.
    Includes chat history, log context and retrieved manual chunks.
    """
    query = state.get("query", "")
    log_summary = state.get("log_summary", "No logs provided.")
    manual_chunks_raw = state.get("retrieved_manual_chunks", [])
    chat_history = state.get("chat_history", [])

    manual_chunks_text = (
        "\n\n---\n\n".join(manual_chunks_raw)
        if manual_chunks_raw
        else "No manuals indexed."
    )

    # Build conversation history block
    history_text = _format_chat_history(chat_history)
    history_block = (
        f"\nPREVIOUS CONVERSATION:\n{history_text}\n"
        if history_text
        else ""
    )

    prompt = f"""You are Chatbot, an expert Industrial Diagnostics Assistant.
Answer the user's query strictly based on the provided context.

CRITICAL SAFETY DIRECTIVE:
- Prioritize operator safety. If an action requires Lockout/Tagout (LOTO) or electrical hazard clearance, state it FIRST in bold.
- Do NOT guess mechanical tolerances, voltage ratings, or torque specifications. Rely strictly on the provided manual chunks.
- If the manual does not contain the troubleshooting steps for a specific fault, state: "Specific remedy not found in indexed manuals. Contact OEM support."
{history_block}
==================================================
CURRENT OPERATING LOGS:
{log_summary}

RELEVANT EXCERPTS FROM EQUIPMENT MANUALS:
{manual_chunks_text}
==================================================

OPERATOR QUERY:
{query}

STRUCTURE YOUR RESPONSE AS FOLLOWS:
1. **Incident / Fault Summary**: (What happened, when, and affected subsystem)
2. **Root Cause Analysis**: (Explanation grounded in the equipment manual)
3. **Corrective Action Procedure**: (Numbered, actionable steps)
4. **Safety & Compliance Notes**: (LOTO, PPE, or safety precautions)
5. **Document Citations**: (Manual title and page/section number)
"""

    messages = [
        {"role": "user", "content": prompt}
    ]

    try:
        response = llm_client.invoke(messages)
        final_answer = response.content
    except Exception as e:
        final_answer = (
            f"⚠️ Error communicating with the model: {str(e)}\n"
            "Please check your API key and connection."
        )

    return {"final_response": final_answer}

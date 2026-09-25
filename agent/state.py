from typing import TypedDict, List, Dict, Optional, Any
from langchain_core.messages import BaseMessage

class IndustrialAgentState(TypedDict):
    # User Inputs
    query: str                                # The user's prompt or question
    chat_history: List[BaseMessage]           # Prior conversation messages

    # Active Session Context
    active_logs: Optional[str]                # Raw text of uploaded telemetry log
    log_filename: str                         # Filename of the uploaded log (for citations)
    has_logs: bool                            # True if log file is loaded in session
    has_manuals: bool                         # True if FAISS vector index contains documents

    # Routing & Processing State
    intent: str                               # "doc_qa" | "log_troubleshoot" | "general"
    extracted_faults: List[str]               # Fault codes/errors identified in logs
    log_summary: str                          # Parsed summary of logs for the prompt
    retrieved_manual_chunks: List[str]        # Relevant excerpts retrieved from FAISS
    sources: List[Dict[str, Any]]             # Manual document names and page numbers cited
    log_citations: List[Dict[str, Any]]       # Log file citations: {source, line, timestamp, level}

    # Final Output
    final_response: str                       # Markdown-formatted diagnostic answer

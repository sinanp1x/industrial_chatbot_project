from typing import Dict, Any
from langchain_core.messages import HumanMessage
from agent.state import IndustrialAgentState

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
        doc_keywords = ["spec", "wiring", "parameter", "maintenance", "sop", "rule", "manual", "guide", "how to", "what is"]
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
            "sources": []
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
        "sources": sources
    }

def analyze_logs_node(state: IndustrialAgentState, vector_store, log_parser) -> IndustrialAgentState:
    """
    Cross-reference active operational logs with equipment manuals to diagnose root causes.
    """
    if not state.get("has_logs", False) or not state.get("active_logs"):
        return {
            "extracted_faults": [],
            "log_summary": "No active logs available.",
            "retrieved_manual_chunks": ["Cannot perform log analysis without logs."]
        }
        
    # Parse the logs
    parsed_data = log_parser.parse_log(state["active_logs"])
    faults = parsed_data["unique_faults"]
    summary = parsed_data["summary_text"]
    
    chunks = []
    sources = []
    
    if state.get("has_manuals", False) and faults:
        # Query FAISS for each fault code
        for fault in faults:
            search_query = f"Troubleshooting procedure for {fault}"
            results = vector_store.search(search_query, k=2)
            for doc in results:
                chunks.append(doc.page_content)
                sources.append({
                    "source": doc.metadata.get("source_file", "Unknown"), 
                    "page": doc.metadata.get("page", 0)
                })
    elif state.get("has_manuals", False):
         # If no specific faults but there are manuals, query based on user query
         results = vector_store.search(state.get("query", ""), k=3)
         for doc in results:
             chunks.append(doc.page_content)
             sources.append({
                 "source": doc.metadata.get("source_file", "Unknown"), 
                 "page": doc.metadata.get("page", 0)
             })
             
    return {
        "extracted_faults": faults,
        "log_summary": summary,
        "retrieved_manual_chunks": chunks,
        "sources": sources
    }

def synthesize_response_node(state: IndustrialAgentState, llm_client) -> IndustrialAgentState:
    """
    Assemble the final grounded response using Hugging Face models.
    """
    query = state.get("query", "")
    log_summary = state.get("log_summary", "No logs provided.")
    manual_chunks_raw = state.get("retrieved_manual_chunks", [])
    
    manual_chunks_text = "\n\n---\n\n".join(manual_chunks_raw) if manual_chunks_raw else "No manuals indexed."
    
    prompt = f"""You are Chatbot, an expert Industrial Diagnostics Assistant.
Answer the user's query strictly based on the provided context.

CRITICAL SAFETY DIRECTIVE:
- Prioritize operator safety. If an action requires Lockout/Tagout (LOTO) or electrical hazard clearance, state it FIRST in bold.
- Do NOT guess mechanical tolerances, voltage ratings, or torque specifications. Rely strictly on the provided manual chunks.
- If the manual does not contain the troubleshooting steps for a specific fault, state: "Specific remedy not found in indexed manuals. Contact OEM support."

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
         final_answer = f"⚠️ Error communicating with Hugging Face API: {str(e)}\nPlease check your API key and connection."

    return {"final_response": final_answer}

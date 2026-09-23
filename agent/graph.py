from langgraph.graph import StateGraph, START, END
from typing import Literal
from agent.state import IndustrialAgentState
from agent.nodes import classify_intent_node, retrieve_knowledge_node, analyze_logs_node, synthesize_response_node

def build_industrial_graph(vector_store, log_parser, llm_client):
    builder = StateGraph(IndustrialAgentState)

    # 1. Define Nodes
    builder.add_node("classify_intent", classify_intent_node)
    builder.add_node("retrieve_knowledge", lambda state: retrieve_knowledge_node(state, vector_store))
    builder.add_node("analyze_logs", lambda state: analyze_logs_node(state, vector_store, log_parser))
    builder.add_node("synthesize_response", lambda state: synthesize_response_node(state, llm_client))

    # 2. Define Conditional Router
    def route_intent(state: IndustrialAgentState) -> Literal["retrieve_knowledge", "analyze_logs", "synthesize_response"]:
        intent = state.get("intent", "general")
        if intent == "doc_qa":
            return "retrieve_knowledge"
        elif intent == "log_troubleshoot":
            return "analyze_logs"
        return "synthesize_response"

    # 3. Add Edges
    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "retrieve_knowledge": "retrieve_knowledge",
            "analyze_logs": "analyze_logs",
            "synthesize_response": "synthesize_response"
        }
    )
    builder.add_edge("retrieve_knowledge", "synthesize_response")
    builder.add_edge("analyze_logs", "synthesize_response")
    builder.add_edge("synthesize_response", END)

    # 4. Compile into executable workflow
    return builder.compile()

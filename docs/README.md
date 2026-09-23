# Industrial Operations & Fault Diagnostics Chatbot (Chatbot)
## Product & Technical Documentation Suite

Welcome to the comprehensive documentation suite for **Chatbot Industrial Assistant** — an intelligent diagnostics and knowledge platform designed for factory floor operators, maintenance engineers, and plant managers.

---

## 📑 Documentation Index

| File | Title | Description |
|---|---|---|
| [01_product_requirements_document.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/01_product_requirements_document.md) | **Product Requirements Document (PRD)** | Core product vision, user personas, problem statement, functional specifications, and KPI metrics. |
| [02_system_architecture_and_tech_stack.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/02_system_architecture_and_tech_stack.md) | **System Architecture & Tech Stack** | Component topology, OpenRouter integration, vector search layer, and data flow. |
| [03_langgraph_workflow_design.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/03_langgraph_workflow_design.md) | **LangGraph Workflow Design** | Clean, logical state machine design, node definitions, transition logic, and failure recovery. |
| [04_rag_and_log_analysis_pipeline.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/04_rag_and_log_analysis_pipeline.md) | **RAG & Telemetry Log Pipeline** | Document ingestion (PDF/TXT), log file parsing, FAISS indexing, and hybrid cross-referencing. |
| [05_ui_ux_specification.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/05_ui_ux_specification.md) | **UI/UX Interface Specification** | Streamlit UI layout, dual-upload file docks, log inspector dashboard, and chat UX. |
| [06_implementation_roadmap_and_milestones.md](file:///c:/Users/user/Desktop/sinan's/chatbot/docs/06_implementation_roadmap_and_milestones.md) | **Implementation Roadmap & Setup Guide** | Phased milestone plan, project folder structure, `requirements.txt`, and verification test plan. |

---

## 🎯 Quick Product Summary

Chatbot bridges the gap between **static industrial documentation** (machinery operating manuals, SOPs, safety guides) and **dynamic telemetry** (PLC event logs, sensor dumps, error logs).

```
   [Equipment Manuals (PDF/TXT)]  ────────> [FAISS Vector Store]
                                                   │
   [Active Logs & Telemetry (TXT)] ──┐             ▼
                                     ├────> [LangGraph Engine] ────> [Actionable Diagnosis & SOP Guidance]
   [Operator Question] ──────────────┘      (Powered by OpenRouter)
```

### Core Value Drivers:
1. **Mean Time to Recovery (MTTR) Reduction**: Operators can paste or upload an error log and receive root-cause analysis in seconds without manual page-turning.
2. **Deterministic & Grounded**: Answers are backed strictly by uploaded equipment manuals with exact section/page citations.
3. **Simplicity First**: Minimal moving parts — no distributed queues or heavyweight database overhead. Runs locally with Streamlit, FAISS, and OpenRouter.

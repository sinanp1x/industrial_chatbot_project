# Implementation Roadmap & Setup Guide
## Project: RoboAI - Industrial Operations & Fault Troubleshooting Assistant

---

## 1. Project Directory Structure

```text
roboai/
│
├── docs/                                  # Architectural & Product Specifications
│   ├── README.md                          # Master documentation index
│   ├── 01_product_requirements_document.md
│   ├── 02_system_architecture_and_tech_stack.md
│   ├── 03_langgraph_workflow_design.md
│   ├── 04_rag_and_log_analysis_pipeline.md
│   ├── 05_ui_ux_specification.md
│   └── 06_implementation_roadmap_and_milestones.md
│
├── agent/                                 # LangGraph State Machine & Agent Logic
│   ├── __init__.py
│   ├── state.py                           # TypedDict IndustrialAgentState definition
│   ├── nodes.py                           # classify_intent, retrieve_knowledge, analyze_logs, synthesize
│   └── graph.py                           # StateGraph definition and compilation
│
├── core/                                  # Core Retrieval & Ingestion Engines
│   ├── __init__.py
│   ├── doc_loader.py                      # PDF/TXT loader and semantic chunker
│   ├── vector_store.py                    # FAISS indexing, embedding, persistence
│   ├── log_parser.py                      # Regex anomaly extractor, timestamp & severity parser
│   └── openrouter_client.py               # OpenRouter ChatOpenAI wrapper
│
├── samples/                               # Sample Industrial Test Datasets
│   ├── sample_manual_press_line.txt       # Sample OEM manual (specs, errors, LOTO)
│   └── sample_shift_telemetry.log         # Sample PLC event log with simulated errors
│
├── storage/                               # Local Persistence (Git-ignored)
│   └── faiss_index/                       # Serialized FAISS index files
│
├── .env.example                           # Template for OPENROUTER_API_KEY
├── requirements.txt                       # Clean, pinned Python dependencies
├── app.py                                 # Streamlit main entrypoint
└── README.md                              # Repository overview and quickstart
```

---

## 2. Dependency Specification (`requirements.txt`)

```text
# Orchestration & Framework
langgraph>=0.2.20
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0

# Vector Store & Embeddings
faiss-cpu>=1.8.0
sentence-transformers>=3.0.0

# Document & Log Processing
pypdf>=4.3.0
pdfplumber>=0.11.0
pandas>=2.2.0

# User Interface
streamlit>=1.38.0

# Utilities & Config
python-dotenv>=1.0.1
pydantic>=2.8.0
```

---

## 3. Phased Implementation Roadmap

```
  [Phase 1] ───> [Phase 2] ───> [Phase 3] ───> [Phase 4] ───> [Phase 5] ───> [Phase 6]
  Environment    Ingestion      Telemetry      LangGraph      Streamlit      E2E Verification
  & Setup        & FAISS        Parser         State Graph    Dashboard      & Testing
```

### Phase 1: Environment & Core Configuration
- Create virtual environment (`python -m venv venv`).
- Install dependencies via `pip install -r requirements.txt`.
- Set up `core/openrouter_client.py` using `ChatOpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`.
- Validate OpenRouter API connectivity with a smoke test.

### Phase 2: Ingestion & FAISS Vector Store Layer (`core/`)
- Implement `core/doc_loader.py`:
  - Support both `.pdf` and `.txt`.
  - Implement `RecursiveCharacterTextSplitter` with safety-aware separators.
- Implement `core/vector_store.py`:
  - Initialize `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")`.
  - Implement `build_index()`, `add_documents()`, `search_similar()`, and `save_to_disk()`.

### Phase 3: Telemetry & Log Parser Module (`core/log_parser.py`)
- Implement regex parsers for ISO/custom timestamps.
- Classify severity levels: `ERROR`, `WARN`, `CRITICAL`, `FATAL`.
- Extract fault codes using pattern matching.
- Generate structured tabular summary for the UI and an aggregated prompt snippet for the LLM.

### Phase 4: LangGraph State Machine (`agent/`)
- Define `IndustrialAgentState` in `agent/state.py`.
- Implement atomic nodes in `agent/nodes.py`:
  - `classify_intent` (Intent router).
  - `retrieve_knowledge` (FAISS similarity search).
  - `analyze_logs` (Cross-references detected log errors with FAISS manual).
  - `synthesize_response` (Grounded generation with citations).
- Construct and compile the graph in `agent/graph.py`.

### Phase 5: Streamlit Industrial Dashboard (`app.py`)
- Implement sidebar:
  - OpenRouter API configuration.
  - Knowledge Base upload dock (PDF/TXT) with real-time indexing status.
  - Telemetry log upload dock with anomaly indicator badges.
- Implement main tabs:
  - Tab 1: Diagnostic Chat with collapsible citations and prompt suggestions.
  - Tab 2: Filterable Log Anomaly Table with metric cards.
  - Tab 3: Knowledge Base browser & vector search tester.
- Inject industrial dark-theme CSS.

### Phase 6: End-to-End Verification & Real-World Simulation
- Prepare realistic test assets in `samples/`:
  - `sample_manual_press_line.txt` with safety warnings and fault codes (`ERR_HYD_OVERPRESS`, `ERR_MOTOR_OVERHEAT`).
  - `sample_shift_telemetry.log` with normal runtime logs leading into an over-pressure trip.
- Validate:
  1. User asks general spec query $\rightarrow$ RAG answers with manual citation.
  2. User uploads log file $\rightarrow$ Log inspector shows error count.
  3. User asks: *"Why did the line stop and what should I do?"* $\rightarrow$ Assistant identifies `ERR_HYD_OVERPRESS`, cites Section 4.2 of the manual, warns about hydraulic pressure hazard, and provides step-by-step resolution.

---

## 4. Verification & Testing Checklist

| Step | Test Objective | Expected Result | Pass/Fail |
|---|---|---|---|
| **T-01** | OpenRouter Connectivity | Successfully returns test completion from selected model. | [ ] |
| **T-02** | PDF & TXT Ingestion | Correctly extracts text and builds FAISS index in `< 10s`. | [ ] |
| **T-03** | Log Anomaly Parser | Correctly detects error lines and extracts error codes. | [ ] |
| **T-04** | LangGraph Loop Execution | Executes cleanly without recursion, circular loops, or timeouts. | [ ] |
| **T-05** | Diagnostic Synthesis | Generates grounded resolution with safety warning and citation. | [ ] |
| **T-06** | Streamlit UI Responsiveness | File uploads update state immediately; tabs switch seamlessly. | [ ] |

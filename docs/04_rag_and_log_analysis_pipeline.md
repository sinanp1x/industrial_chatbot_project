# RAG & Telemetry Log Pipeline Specification
## Project: Chatbot - Industrial Operations & Fault Troubleshooting Assistant

---

## 1. Dual-Stream Pipeline Overview

Industrial environments require handling two fundamentally different data profiles:
1. **Static Knowledge Stream**: Structured technical manuals, safety SOPs, circuit diagrams, and mechanical specifications. (Queried via dense vector retrieval).
2. **Dynamic Telemetry Stream**: Unstructured, high-frequency, time-stamped text files containing error codes, alarms, and operating logs. (Queried via structured pattern parsing + targeted cross-retrieval).

```
   STREAM 1: STATIC MANUALS (PDF / TXT)
   ┌─────────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
   │ PDF / TXT   │ ──> │ Document Parser      │ ──> │ Semantic Chunking   │ ──> │ FAISS Vector    │
   │ Upload      │     │ (pypdf / pdfplumber) │     │ (Size: 900, Ov: 120)│     │ Store (MiniLM)  │
   └─────────────┘     └──────────────────────┘     └─────────────────────┘     └────────┬────────┘
                                                                                         │
   STREAM 2: DYNAMIC LOGS (TXT / LOG)                                                    │ Match
   ┌─────────────┐     ┌──────────────────────┐     ┌─────────────────────┐              │ Faults
   │ Log / TXT   │ ──> │ Regex Event Parser   │ ──> │ Anomaly Extractor   │ ─────────────┘
   │ Upload      │     │ (Timestamps, Levels) │     │ (Fault Codes/Spikes)│
   └─────────────┘     └──────────────────────┘     └──────────┬──────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │ Augmented Prompt to │
                                                    │ OpenRouter API      │
                                                    └─────────────────────┘
```

---

## 2. Stream 1: Static Knowledge Ingestion Pipeline

### 2.1 Extraction
- **PDF Documents**: Handled via `pypdf` with fallback to `pdfplumber` for complex tables or multi-column layouts.
- **Plain Text / Markdown**: Direct UTF-8 ingestion with line-break normalization.
- **Metadata Tagging**: Each extracted page retains metadata:
  ```json
  {
    "source_file": "ABB_IRB6700_Maintenance_Manual.pdf",
    "page": 42,
    "chunk_id": "ABB_IRB6700_Maintenance_Manual.pdf_p42_c1",
    "doc_type": "manual"
  }
  ```

### 2.2 Semantic Chunking Strategy
Industrial manuals feature dense safety warnings, parameter tables, and sequential steps. Standard naive splitting can sever a warning header from its instructions.
- **Splitter**: `RecursiveCharacterTextSplitter`
- **Separators**: `["\n\n### ", "\n\n## ", "\n\nDANGER:", "\n\nWARNING:", "\n\n", "\n", " "]`
- **Chunk Size**: `850` characters.
- **Chunk Overlap**: `150` characters (ensures safety warnings overlap into the subsequent action steps).

### 2.3 Embedding & Vector Indexing (FAISS)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
  - 384 dimensions.
  - Executes locally on CPU (< 15ms per chunk).
  - Normalized embeddings for exact Cosine Similarity matching via `faiss.IndexFlatIP`.
- **Persistence**:
  - The FAISS index and docstore are serialized to `storage/faiss_index/` using `save_local()` and reloaded via `load_local(..., allow_dangerous_deserialization=True)`.
  - Incremental document additions update the existing index without re-indexing prior manuals.

---

## 3. Stream 2: Dynamic Telemetry & Log Ingestion Pipeline

### 3.1 Log File Characteristics
Industrial logs typically adhere to formats like:
```text
2026-09-23 14:15:02.124 [WARN] LINE_3_PRESS Hydraulic pressure 185 bar exceeds nominal (160 bar)
2026-09-23 14:15:10.589 [ERROR] LINE_3_PRESS Fault code ERR_HYD_OVERPRESS tripped emergency relief valve
2026-09-23 14:15:12.001 [FATAL] LINE_3_PRESS Automated shutdown initiated by safety PLC
```

### 3.2 Ingestion & Anomaly Detection Routine
Unlike vectorizing the entire 50,000-line log into FAISS, the system uses a fast, deterministic log scanner:
1. **Timestamp Normalizer**: Recognizes standard formats (`YYYY-MM-DD HH:MM:SS`, ISO-8601, UNIX epoch).
2. **Severity Filter**: Categorizes lines into `[INFO]`, `[WARN]`, `[ERROR]`, `[FATAL]`, `[CRITICAL]`.
3. **Fault Code Extractor**: Uses regex patterns:
   - `\b(?:ERR|FAULT|ALARM|CODE|E)[-_]?[0-9A-Z]{3,8}\b`
   - Numeric industrial codes (e.g., Siemens `F07800`, Fanuc `SRVO-062`).
4. **Windowing & Deduping**:
   - Groups recurring errors (e.g., "Fault ERR_HYD_OVERPRESS occurred 14 times between 14:15:00 and 14:15:30").
   - Retains the most recent 30 critical lines to prevent prompt buffer blowout.

---

## 4. Cross-Referencing Logic: Connecting Logs to Manuals

When a user asks: *"Why did the press stop and what do we do?"*, the pipeline executes:

1. **Step 1 - Isolate Active Fault Codes**:
   - Extracted from logs: `ERR_HYD_OVERPRESS`.
2. **Step 2 - Target Query Formulation**:
   - Synthesizes search query: `"ERR_HYD_OVERPRESS hydraulic pressure relief valve reset troubleshooting"`.
3. **Step 3 - FAISS Query**:
   - Retrieves top 3 chunks from `ABB_Press_Manual.pdf` describing hydraulic pressure thresholds and relief valve manual reset procedures.
4. **Step 4 - Prompt Assembly**:
   - Combines log context + retrieved manual section + operator question.
5. **Step 5 - Grounded Synthesis via OpenRouter**:
   - The LLM synthesizes an action plan referencing both the machine state and the vendor's documented procedure.

---

## 5. Industrial Prompt Template

```python
INDUSTRIAL_DIAGNOSTIC_PROMPT = """
You are Chatbot, an industrial maintenance and operations engineering assistant.
Analyze the following machine telemetry and reference manuals to answer the operator's query.

CRITICAL SAFETY DIRECTIVE:
- Prioritize operator safety. If an action requires Lockout/Tagout (LOTO) or electrical hazard clearance, state it FIRST in bold.
- Do NOT guess mechanical tolerances, voltage ratings, or torque specifications. Rely strictly on the provided manual chunks.
- If the manual does not contain the troubleshooting steps for a specific fault, state: "Specific remedy not found in indexed manuals. Contact OEM support."

==================================================
ACTIVE MACHINE TELEMETRY & DETECTED ANOMALIES:
{log_summary}

RELEVANT EXCERPTS FROM EQUIPMENT MANUALS:
{manual_chunks}
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
```

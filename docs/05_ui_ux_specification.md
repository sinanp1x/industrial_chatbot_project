# UI/UX Interface Specification
## Project: RoboAI - Industrial Operations & Fault Troubleshooting Assistant

---

## 1. Design Principles for Industrial Environments

Industrial applications require high clarity, immediate information hierarchy, and error-proof operation. The UI is built using **Streamlit** styled with an industrial engineering aesthetic (slate, dark obsidian, status amber, and emergency crimson).

### Key UX Directives:
1. **Zero Clutter**: Operators under shift pressure need answers in seconds. No extraneous decorative widgets.
2. **Dual-Dock Ingestion**: Clear visual separation between **Static Manuals (Library)** and **Active Shift Logs (Telemetry)**.
3. **Safety First**: Emergency alerts and Lockout/Tagout (LOTO) notices must visually pop with distinct callout banners.
4. **Verifiable Citations**: Every recommendation includes expandable cards revealing the exact page and paragraph from the OEM manual.

---

## 2. Layout Structure & Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🏭 RoboAI | Industrial Copilot & Equipment Diagnostics                 [Model: Claude 3.5 Sonnet] [Status: ● Ready] │
├───────────────────────────────┬─────────────────────────────────────────────────────────────────────────────┤
│ SIDEBAR DOCK                  │ MAIN VIEWPORT TABS                                                          │
│                               │ ┌──────────────────────┬──────────────────────┬──────────────────────────┐  │
│ ⚙️ Configuration              │ │ 💬 Diagnostic Chat   │ 📊 Log Anomaly Table │ 📚 Manuals Knowledge Base│  │
│ - OpenRouter API Key [•••••]  │ └──────────────────────┴──────────────────────┴──────────────────────────┘  │
│ - Model Selector [Dropdown]   │                                                                             │
│                               │  [ASSISTANT]                                                                │
│ 📚 Knowledge Base (Manuals)   │  🚨 Fault Detected at 14:15:10: ERR_HYD_OVERPRESS (Line 3 Press)             │
│ [Drag & drop PDF / TXT]       │                                                                             │
│ • Fanuc_R2000_Manual.pdf (14) │  **Root Cause Analysis:**                                                   │
│ • Press_Line3_SOP.txt (5)     │  According to the Press Safety Manual (Section 4.2), hydraulic pressure      │
│ [Re-index Button] [Clear]     │  exceeded 180 bar due to relief valve obstruction.                          │
│                               │                                                                             │
│ ⚡ Active Telemetry / Logs    │  **Recommended Action:**                                                    │
│ [Drag & drop .txt / .log]     │  1. Initiate immediate Lockout/Tagout (LOTO) on Valve V-12.                 │
│ Status: 2 Errors, 4 Warnings  │  2. Bleed return manifold according to Step 3.2.                            │
│                               │                                                                             │
│ [Clear Logs Button]           │  ▼ Sources Cited (Click to expand)                                          │
│                               │    ├─ Press_Line3_SOP.txt (Lines 112-140)                                   │
│                               │    └─ Fanuc_R2000_Manual.pdf (Page 48)                                      │
│                               ├─────────────────────────────────────────────────────────────────────────────┤
│                               │ [💬 Ask about equipment specs, manual rules, or diagnose current log...]    │
└───────────────────────────────┴─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Sidebar Specification

### 3.1 Global Configuration Panel
- **API Key Input**: `st.sidebar.text_input("OpenRouter API Key", type="password")`
  - Validates key structure. Persisted in `st.session_state`.
- **Model Selector**:
  - `anthropic/claude-3.5-sonnet` (Default for deep industrial diagnostics).
  - `deepseek/deepseek-chat` (Ultra-fast, cost-effective).
  - `openai/gpt-4o-mini` (General operational queries).
  - `meta-llama/llama-3.1-70b-instruct` (Open-source powerhouse).

### 3.2 Knowledge Base Ingestion Dock (Manuals & SOPs)
- **Component**: `st.sidebar.file_uploader("Upload Manuals & SOPs", type=["pdf", "txt"], accept_multiple_files=True)`
- **Feedback Indicators**:
  - Badge: `🟢 Index Ready (3 Documents, 84 Chunks)` or `⚪ No manuals loaded`.
  - Document List: File name, file size, and page/chunk count chips.
  - Action: "Re-index All" and "Clear Knowledge Base" buttons.

### 3.3 Active Telemetry Ingestion Dock (Logs & Data)
- **Component**: `st.sidebar.file_uploader("Upload Shift Logs / Fault Data", type=["txt", "log", "csv"])`
- **Feedback Indicators**:
  - Anomaly Status Pill: `🔴 3 Critical Errors Detected` / `🟡 5 Warnings` / `🟢 Clean Log`.
  - Primary Error Chip: Displays top detected fault code (e.g., `ERR_M1_OVERHEAT`).
  - Action: "Flush Active Log" button.

---

## 4. Main Viewport Tabs Specification

### Tab 1: Diagnostic Chat & Assistant (`st.chat_message`)
- **Quick-Action Prompt Chips**:
  - 🔍 *"Diagnose all errors in the uploaded log"*
  - 📖 *"What are the weekly maintenance steps for Motor M1?"*
  - ⚠️ *"List safety precautions and LOTO procedure for line stoppage"*
  - 🔧 *"Explain fault code ERR_HYD_OVERPRESS and give remedy"*
- **Message Rendering**:
  - User query bubble.
  - Assistant response rendered in structured markdown with syntax highlighting.
  - Direct collapsible expanders (`st.expander("📖 Cited Manual Excerpts")`) revealing the exact source chunks.

### Tab 2: Log Anomaly Table & Telemetry Inspector
- **KPI Metrics Cards**:
  - Total Log Entries (`st.metric("Total Lines", 412)`)
  - Warning Events (`st.metric("Warnings", 6)`)
  - Critical / Fatal Events (`st.metric("Errors/Fatal", 2, delta_color="inverse")`)
  - Detected Fault Codes (`st.metric("Unique Faults", 1)`)
- **Interactive Data Table**:
  - Columns: `Timestamp`, `Level`, `Subsystem`, `Message`, `Detected Code`.
  - Filterable by log level (`ERROR`, `WARN`, `INFO`).
- **Raw Log Viewer**:
  - Expandable text box with copy-to-clipboard for quick inspection.

### Tab 3: Knowledge Base Explorer
- **Indexed Document Table**:
  - Columns: `Filename`, `Type`, `Size`, `Total Chunks`, `Status`.
- **Search Sandbox**:
  - Allows operators to perform raw vector queries to test what document sections match a given term.

---

## 5. Industrial Design Theme & Custom CSS Tokens

To ensure an industrial look and feel, custom CSS will be injected into Streamlit:
```css
/* Industrial Palette Tokens */
:root {
  --bg-industrial: #0e1117;
  --surface-card: #1a1f2c;
  --border-subtle: #2d3748;
  --accent-blue: #3182ce;
  --safety-amber: #d69e2e;
  --emergency-red: #e53e3e;
  --text-primary: #f7fafc;
}

/* Safety & Callout Banner */
.safety-alert {
  background-color: rgba(229, 62, 62, 0.15);
  border-left: 4px solid #e53e3e;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
}
```

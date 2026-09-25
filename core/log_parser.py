import re
from typing import List, Dict, Optional, Tuple


class LogParser:
    """
    Format-agnostic log parser.

    Instead of enforcing a specific log format (timestamp + [LEVEL] + subsystem),
    the parser applies a series of heuristics that work on arbitrary log files:
      - Any line containing error/fault keywords is flagged as an anomaly.
      - Timestamps are detected via multiple common patterns (optional).
      - Severity is inferred from keywords anywhere in the line.
      - Fault codes are detected via broad patterns.
      - Every entry carries its 1-based line number so the chatbot can cite
        "log_file.log : L42" just like it cites "manual.pdf : page 7".
    """

    # Common timestamp patterns (most specific first)
    _TS_PATTERNS = [
        # ISO-8601 and variants: 2026-09-23T14:15:10.589Z
        re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
        # DD-MM-YYYY HH:MM:SS
        re.compile(r"\d{2}[-/]\d{2}[-/]\d{4}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"),
        # HH:MM:SS only
        re.compile(r"\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"),
        # Unix epoch (seconds or ms)
        re.compile(r"\b\d{10,13}\b"),
    ]

    # Severity inference - keyword sets searched anywhere in the line (case-insensitive)
    # Ordered from most severe to least so first match wins
    _SEVERITY_MAP: List[Tuple[str, List[str]]] = [
        ("FATAL",   ["fatal", "critical", "emergency", "catastrophic", "system crash", "core dump"]),
        ("ERROR",   ["error", "err ", "err_", " err:", "failed", "failure", "exception", "fault",
                     "alarm", "trip", "shutdown", "halted", "panic", "rejected", "corrupt"]),
        ("WARN",    ["warn", "warning", "caution", "high ", "overload", "overpress",
                     "overheat", "overvolt", "limit", "threshold", "nearing", "exceeded"]),
        ("INFO",    ["info", "start", "stop", "normal", "ok", "success", "ready", "operating",
                     "complete", "initialized", "connected"]),
    ]

    # Broad fault-code pattern: alphanumeric tokens that look like codes
    # Explicitly excludes bare log level names (INFO/WARN/WARNING/ERROR/FATAL/CRITICAL)
    _FAULT_CODE_RE = re.compile(
        r"(?<![\[\w])"   # not preceded by [ or word char (avoids matching [ERROR])
        r"\b(?:"
        r"(?:ERR|FAULT|ALARM|CODE|F|A)[-_]?[0-9A-Z]{2,15}"   # prefixed codes: ERR_HYD_01, F-104
        r"|E[-_][0-9A-Z]{2,15}"                                # E-104, E_042 (E only with separator)
        r"|[A-Z]{2,8}_[A-Z0-9]{2,15}"                         # SNAKE_UPPER: HYD_OVERPRESS
        r"|[A-Z]\d{3,6}"                                       # Letter+digits: E1042
        r")\b"
        r"(?![\]\w])"   # not followed by ] or word char
    )

    # Log level tokens to strip from message display
    _LEVEL_STRIP_RE = re.compile(r"\[(INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\]", re.IGNORECASE)

    def parse_log(self, log_content: str, source_filename: str = "log") -> Dict:
        """
        Parse raw log text into structured entries.

        Args:
            log_content:      Raw text content of the log file.
            source_filename:  Name of the log file (used for citations).

        Returns a dict with:
            entries        - list of all parsed line dicts
            anomalies      - subset of entries with WARN / ERROR / FATAL severity
            counts         - dict of severity -> count
            unique_faults  - deduplicated list of detected fault codes
            summary_text   - human-readable text block for the LLM prompt
            log_citations  - list of citation dicts {"source", "line", "timestamp", "level"}
        """
        lines = log_content.splitlines()
        parsed_entries: List[Dict] = []
        extracted_faults: set = set()
        counts = {"INFO": 0, "WARN": 0, "ERROR": 0, "FATAL": 0}

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            entry: Dict = {
                "line_number": line_no,
                "raw": raw_line,
                "timestamp": None,
                "level": "INFO",
                "message": line,
                "fault_codes": [],
                "source": source_filename,
            }

            # --- Timestamp detection ---
            for ts_pat in self._TS_PATTERNS:
                ts_match = ts_pat.search(line)
                if ts_match:
                    entry["timestamp"] = ts_match.group(0)
                    break

            # --- Severity detection (first keyword match wins, most severe first) ---
            line_lower = line.lower()
            detected_level = "INFO"
            for level, keywords in self._SEVERITY_MAP:
                if any(kw in line_lower for kw in keywords):
                    detected_level = level
                    break
            entry["level"] = detected_level
            counts[detected_level] = counts.get(detected_level, 0) + 1

            # --- Fault code extraction ---
            faults = self._FAULT_CODE_RE.findall(line)
            if faults:
                entry["fault_codes"] = faults
                extracted_faults.update(faults)

            parsed_entries.append(entry)

        # Anomalies = anything WARN or worse
        anomalies = [e for e in parsed_entries if e["level"] in ("WARN", "ERROR", "FATAL")]
        # Limit to the most recent 40 anomalies to stay within token budget
        recent_anomalies = anomalies[-40:]

        # Build log-citation objects (parallel to knowledge-base "sources")
        log_citations = [
            {
                "source": e["source"],
                "line": e["line_number"],
                "timestamp": e["timestamp"] or "N/A",
                "level": e["level"],
            }
            for e in recent_anomalies
        ]

        return {
            "entries": parsed_entries,
            "anomalies": recent_anomalies,
            "counts": counts,
            "unique_faults": list(extracted_faults),
            "summary_text": self._build_summary(recent_anomalies, source_filename),
            "log_citations": log_citations,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_summary(self, anomalies: List[Dict], filename: str) -> str:
        """
        Build a concise, citation-tagged summary block for the LLM prompt.
        Each anomaly line is tagged with [filename:L<line_no>] so the LLM
        can reference specific log lines in its answer.
        """
        if not anomalies:
            return "No warnings, errors, or fault codes detected in the provided log."

        out_lines = [f"LOG ANOMALIES FROM [{filename}]:"]
        for e in anomalies:
            ts    = e["timestamp"] or "?"
            lvl   = e["level"]
            # Build a clean message: strip the detected timestamp and level brackets from display
            msg   = self._LEVEL_STRIP_RE.sub("", e["raw"]).strip()
            if e["timestamp"]:
                msg = msg.replace(e["timestamp"], "").strip().lstrip("-: ").strip()
            codes = f"  -> Fault codes: {', '.join(e['fault_codes'])}" if e["fault_codes"] else ""
            tag   = f"[{filename}:L{e['line_number']}]"
            out_lines.append(f"  {tag} [{ts}] [{lvl}] {msg}{codes}")

        return "\n".join(out_lines)

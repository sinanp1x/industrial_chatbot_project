import re
import pandas as pd
from typing import List, Dict

class LogParser:
    def __init__(self):
        # Matches typical standard timestamp (e.g. 2026-09-23 14:15:10.589 or 2026-09-23 14:15:10)
        self.timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d{3})?")
        
        # Matches log levels
        self.level_pattern = re.compile(r"\[(INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\]")
        
        # Matches fault codes like ERR_HYD_OVERPRESS, E-104, FAULT_01
        self.fault_code_pattern = re.compile(r"\b(?:ERR|FAULT|ALARM|CODE|E)[-_]?[0-9A-Z]{3,15}\b")

    def parse_log(self, log_content: str) -> Dict:
        """
        Parses raw log text and extracts timestamps, severity, and fault codes.
        Returns a dictionary containing structured data and identified anomalies.
        """
        lines = log_content.splitlines()
        parsed_entries = []
        extracted_faults = set()
        
        counts = {"INFO": 0, "WARN": 0, "ERROR": 0, "FATAL": 0}

        for line in lines:
            if not line.strip():
                continue
                
            entry = {
                "timestamp": None,
                "level": "INFO",
                "subsystem": "UNKNOWN",
                "message": line.strip(),
                "fault_codes": []
            }

            # Extract Timestamp
            ts_match = self.timestamp_pattern.search(line)
            if ts_match:
                entry["timestamp"] = ts_match.group(0)
                
            # Extract Level
            level_match = self.level_pattern.search(line)
            if level_match:
                level = level_match.group(1).upper()
                if level == "WARNING": level = "WARN"
                if level == "CRITICAL": level = "FATAL"
                entry["level"] = level
                if level in counts:
                    counts[level] += 1
            else:
                counts["INFO"] += 1
                
            # Naive Subsystem Extraction (word right after level)
            if level_match:
                parts = line[level_match.end():].strip().split()
                if parts:
                    entry["subsystem"] = parts[0]
                    entry["message"] = " ".join(parts[1:])
            
            # Extract Fault Codes
            faults = self.fault_code_pattern.findall(line)
            if faults:
                entry["fault_codes"] = faults
                for fault in faults:
                    extracted_faults.add(fault)
                    
            parsed_entries.append(entry)

        # Filter to only warnings and errors for the context window
        anomalies = [e for e in parsed_entries if e["level"] in ["WARN", "ERROR", "FATAL"]]
        # Keep recent 30
        recent_anomalies = anomalies[-30:] if anomalies else []

        return {
            "entries": parsed_entries,
            "anomalies": recent_anomalies,
            "counts": counts,
            "unique_faults": list(extracted_faults),
            "summary_text": self._build_summary_text(recent_anomalies)
        }

    def _build_summary_text(self, anomalies: List[Dict]) -> str:
        if not anomalies:
            return "No critical errors or warnings detected in the provided log."
            
        summary = "RECENT ANOMALIES:\n"
        for entry in anomalies:
            ts = entry['timestamp'] or "UNKNOWN_TIME"
            lvl = entry['level']
            msg = entry['message']
            codes = f" [Codes: {','.join(entry['fault_codes'])}]" if entry['fault_codes'] else ""
            summary += f"[{ts}] [{lvl}] {msg}{codes}\n"
        return summary

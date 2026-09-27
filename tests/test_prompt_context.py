from agent.nodes import synthesize_response_node


class FakeLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, messages):
        self.prompt = messages[0]["content"]
        return type("Response", (), {"content": "ok"})()


def test_synthesis_prompt_keeps_original_log_with_analysis_and_citations():
    original_log = """2026-09-27 10:00:00 [INFO] UNIQUE_NORMAL_LINE press line operating normally
2026-09-27 10:05:00 [ERROR] UNIQUE_LATE_ERROR_LINE hydraulic pressure trip"""
    llm = FakeLLM()

    synthesize_response_node(
        {
            "query": "What happened?",
            "active_logs": original_log,
            "has_logs": True,
            "has_manuals": False,
            "log_summary": "LOG ANOMALIES FROM [shift.log]: [shift.log:L2] hydraulic pressure trip",
            "extracted_faults": ["ERR_HYD_OVERPRESS"],
            "log_citations": [
                {"source": "shift.log", "line": 2, "timestamp": "10:05:00", "level": "ERROR"}
            ],
            "retrieved_manual_chunks": [],
            "chat_history": [],
        },
        llm,
    )

    assert "ORIGINAL LOG DATA" in llm.prompt
    assert "UNIQUE_NORMAL_LINE" in llm.prompt
    assert "UNIQUE_LATE_ERROR_LINE" in llm.prompt
    assert "DERIVED LOG ANALYSIS" in llm.prompt
    assert "[shift.log:L2]" in llm.prompt
from core.log_parser import LogParser


def test_parse_log_preserves_blank_lines_and_original_text():
    content = "\n2026-09-27T10:00:00Z,ERROR,ERR_BETA,first\n\n10:01:00,ERROR,ERR_ALPHA,second\n"

    result = LogParser().parse_log(content, source_filename="events.csv")

    assert result["raw_text"] == content
    assert [entry["line_number"] for entry in result["entries"]] == [1, 2, 3, 4]
    assert result["entries"][0]["is_blank"] is True
    assert result["entries"][2]["is_blank"] is True
    assert result["entries"][1]["raw"] == "2026-09-27T10:00:00Z,ERROR,ERR_BETA,first"
    assert result["counts"] == {"INFO": 0, "WARN": 0, "ERROR": 2, "FATAL": 0}


def test_parse_log_keeps_fault_order_and_summary_stable_for_csv_like_logs():
    content = (
        "2026-09-27T10:00:00Z,ERROR,ERR_BETA,first\n"
        "10:01:00,ERROR,ERR_ALPHA,second\n"
        "10:02:00,ERROR,ERR_BETA,repeat\n"
    )
    parser = LogParser()

    first = parser.parse_log(content, source_filename="events.csv")
    second = parser.parse_log(content, source_filename="events.csv")

    assert first["unique_faults"] == ["ERR_BETA", "ERR_ALPHA"]
    assert first["unique_faults"] == second["unique_faults"]
    assert first["summary_text"] == second["summary_text"]
    assert all("ERROR" not in entry["fault_codes"] for entry in first["entries"])
    assert [citation["line"] for citation in first["log_citations"]] == [1, 2, 3]

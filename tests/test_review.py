import pytest

from claude_review.review import REPORT_TOOL, ReviewError, parse_review, review_diff


def test_sends_diff_and_forces_the_report_tool(fake_client):
    client = fake_client({"summary": "Adds a helper.", "findings": []})
    review = review_diff(client, "diff --git a/x b/x", model="some-model")

    call = client.calls[0]
    assert call["model"] == "some-model"
    assert call["tools"] == [REPORT_TOOL]
    assert call["tool_choice"] == {"type": "tool", "name": "report_findings"}
    assert "diff --git a/x b/x" in call["messages"][0]["content"]
    assert review.summary == "Adds a helper."
    assert review.findings == []
    assert review.worst() is None


def test_findings_are_sorted_by_severity_then_location():
    review = parse_review(
        {
            "summary": "",
            "findings": [
                {"file": "b.py", "line": 3, "severity": "low", "message": "nit"},
                {"file": "a.py", "line": 9, "severity": "high", "message": "crash"},
                {"file": "a.py", "line": 2, "severity": "high", "message": "sql injection"},
            ],
        }
    )
    assert [(f.file, f.line) for f in review.findings] == [("a.py", 2), ("a.py", 9), ("b.py", 3)]
    assert review.worst() == "high"


def test_bad_values_from_the_model_are_cleaned_up():
    review = parse_review(
        {
            "summary": "x",
            "findings": [
                {
                    "file": "a.py",
                    "line": 0,
                    "severity": "CRITICAL",
                    "message": " msg ",
                    "suggestion": "",
                }
            ],
        }
    )
    f = review.findings[0]
    assert (f.severity, f.line, f.message, f.suggestion) == ("low", None, "msg", None)


def test_missing_tool_call_is_an_error(fake_client):
    from types import SimpleNamespace

    client = fake_client(content=[SimpleNamespace(type="text", text="Looks good!")])
    with pytest.raises(ReviewError):
        review_diff(client, "diff", model="m")

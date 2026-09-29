import json

from rich.console import Console

from claude_review.render import print_text, to_json, to_markdown
from claude_review.review import Finding, Review

REVIEW = Review(
    summary="Adds retry logic.",
    findings=[
        Finding("api.py", "high", "Retries forever on 4xx.", 42, "Only retry on 5xx and timeouts."),
        Finding("api.py", "low", "Magic number | 3.", None),
    ],
)


def test_text_output():
    console = Console(record=True, width=100)
    print_text(REVIEW, console)
    out = console.export_text()
    assert "HIGH   api.py:42" in out
    assert "→ Only retry on 5xx" in out
    assert "1 high, 1 low" in out


def test_text_output_when_clean():
    console = Console(record=True)
    print_text(Review(summary="", findings=[]), console)
    assert "No issues found." in console.export_text()


def test_markdown_escapes_pipes():
    md = to_markdown(REVIEW)
    assert "| high | `api.py:42` | Retries forever on 4xx.<br>**Suggestion:** Only retry" in md
    assert "Magic number \\| 3." in md


def test_json_round_trips():
    data = json.loads(to_json(REVIEW))
    assert data["findings"][0] == {
        "file": "api.py",
        "severity": "high",
        "message": "Retries forever on 4xx.",
        "line": 42,
        "suggestion": "Only retry on 5xx and timeouts.",
    }

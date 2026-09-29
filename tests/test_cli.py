import json

import pytest

from claude_review.cli import main, should_fail

from .conftest import git

FINDINGS = {
    "summary": "Changes add() to subtract.",
    "findings": [
        {"file": "app.py", "line": 2, "severity": "medium", "message": "add() now subtracts."}
    ],
}


@pytest.fixture
def staged(repo):
    (repo / "app.py").write_text("def add(a, b):\n    return a - b\n")
    git(repo, "add", "app.py")
    return repo


@pytest.mark.parametrize(
    "worst, threshold, fails",
    [
        ("high", "high", True),
        ("medium", "high", False),
        ("medium", "medium", True),
        ("low", "medium", False),
        ("high", "never", False),
        (None, "low", False),
    ],
)
def test_should_fail(worst, threshold, fails):
    assert should_fail(worst, threshold) is fails


def test_nothing_staged(repo, fake_client, capsys):
    client = fake_client(FINDINGS)
    assert main([], client=client) == 0
    assert client.calls == []
    assert "Nothing to review" in capsys.readouterr().err


def test_exit_code_follows_fail_on(staged, fake_client):
    assert main([], client=fake_client(FINDINGS)) == 0
    assert main(["--fail-on", "medium"], client=fake_client(FINDINGS)) == 1


def test_json_output(staged, fake_client, capsys):
    main(["--format", "json"], client=fake_client(FINDINGS))
    data = json.loads(capsys.readouterr().out)
    assert data["findings"][0]["message"] == "add() now subtracts."


def test_missing_api_key(staged, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main([]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_api_errors_are_reported_not_raised(staged, capsys):
    class Broken:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("connection reset")

    assert main([], client=Broken()) == 2
    assert "connection reset" in capsys.readouterr().err


def test_model_can_be_set_from_env(staged, fake_client, monkeypatch):
    monkeypatch.setenv("CLAUDE_REVIEW_MODEL", "claude-haiku-4-5")
    client = fake_client(FINDINGS)
    main([], client=client)
    assert client.calls[0]["model"] == "claude-haiku-4-5"

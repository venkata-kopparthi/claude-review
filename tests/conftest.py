import subprocess
from types import SimpleNamespace

import pytest


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "dev@example.com")
    git(tmp_path, "config", "user.name", "Dev")
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class FakeClient:
    """Stands in for anthropic.Anthropic and records what it was asked."""

    def __init__(self, tool_input=None, content=None):
        self.calls = []
        blocks = content
        if blocks is None:
            blocks = [SimpleNamespace(type="tool_use", input=tool_input or {})]
        self._response = SimpleNamespace(content=blocks)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


@pytest.fixture
def fake_client():
    return FakeClient

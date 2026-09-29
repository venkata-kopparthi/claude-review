import pytest

from claude_review.git import GitError, filter_diff, get_diff

from .conftest import git


def test_staged_changes_only(repo):
    (repo / "app.py").write_text("def add(a, b):\n    return a - b\n")
    assert get_diff() == ""

    git(repo, "add", "app.py")
    diff = get_diff()
    assert "-    return a + b" in diff
    assert "+    return a - b" in diff


def test_diff_against_base_branch(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "new.py").write_text("print('hi')\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add new.py")

    diff = get_diff(base="main")
    assert "diff --git a/new.py b/new.py" in diff


def test_lockfiles_and_binaries_are_skipped(repo):
    (repo / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
    (repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    (repo / "util.py").write_text("x = 1\n")
    git(repo, "add", ".")

    diff = get_diff()
    assert "util.py" in diff
    assert "package-lock.json" not in diff
    assert "logo.png" not in diff


def test_outside_a_repo_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(GitError):
        get_diff()


def test_unknown_base_raises(repo):
    with pytest.raises(GitError):
        get_diff(base="does-not-exist")


def test_filter_keeps_normal_files():
    diff = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"
        "diff --git a/yarn.lock b/yarn.lock\n--- a/yarn.lock\n+++ b/yarn.lock\n"
        "@@ -1 +1 @@\n-a\n+b\n"
    )
    out = filter_diff(diff)
    assert "a/a.py" in out
    assert "yarn.lock" not in out

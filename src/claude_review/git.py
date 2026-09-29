import subprocess
from fnmatch import fnmatch

# Files that are noisy to review and rarely hide real bugs.
SKIP_PATTERNS = [
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "*.min.js",
    "*.map",
    "*.svg",
    "*.snap",
]


class GitError(Exception):
    pass


def _run(args: list[str], cwd: str | None = None) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        raise GitError("git is not installed or not on PATH") from e
    except subprocess.CalledProcessError as e:
        raise GitError(e.stderr.strip() or f"git {' '.join(args)} failed") from e
    return result.stdout


def get_diff(base: str | None = None, cwd: str | None = None) -> str:
    """Staged changes by default, or everything since `base` (e.g. "main")."""
    _run(["rev-parse", "--is-inside-work-tree"], cwd)
    if base:
        merge_base = _run(["merge-base", base, "HEAD"], cwd).strip()
        args = ["diff", merge_base]
    else:
        args = ["diff", "--cached"]
    return filter_diff(_run([*args, "--unified=5", "--no-color"], cwd))


def filter_diff(diff: str) -> str:
    """Drop lockfiles, generated files and binary diffs."""
    kept: list[str] = []
    for chunk in split_files(diff):
        path = chunk_path(chunk)
        if path and any(fnmatch(path.rsplit("/", 1)[-1], p) for p in SKIP_PATTERNS):
            continue
        if any(line.startswith("Binary files ") for line in chunk.splitlines()):
            continue
        kept.append(chunk)
    return "".join(kept)


def split_files(diff: str) -> list[str]:
    chunks: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git ") or not chunks:
            chunks.append(line)
        else:
            chunks[-1] += line
    return chunks


def chunk_path(chunk: str) -> str | None:
    first = chunk.split("\n", 1)[0]
    if not first.startswith("diff --git "):
        return None
    return first.split(" b/", 1)[-1].strip()

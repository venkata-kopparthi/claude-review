# claude-review

A small CLI that sends your staged git changes (or a whole branch) to Claude and prints back the problems a careful reviewer would flag: bugs, security issues, missing error handling. Style nits are left to your linter.

```
$ git add -A
$ claude-review
Adds retry logic to the payments client.

HIGH   src/payments/client.py:42
       Retries on every exception, including 4xx responses, so a bad card is charged repeatedly.
       → Only retry on 5xx responses and timeouts.

MEDIUM src/payments/client.py:57
       `backoff` is never reset after a successful call.

1 high, 1 medium
```

## Install

Requires Python 3.11+ and git.

```bash
pip install git+https://github.com/venkata-kopparthi/claude-review.git
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
claude-review                      # review staged changes
claude-review --base main          # review everything on this branch since main
claude-review --format markdown    # output a markdown table (e.g. for a PR comment)
claude-review --format json        # machine-readable output
claude-review --fail-on medium     # exit 1 on medium or high findings
```

| Option | Default | |
| --- | --- | --- |
| `--base BRANCH` | — | Diff against the merge base with `BRANCH` instead of reviewing staged changes |
| `--format` | `text` | `text`, `markdown` or `json` |
| `--fail-on` | `high` | `high`, `medium`, `low` or `never` |
| `--model` | `claude-sonnet-5` | Also settable with `CLAUDE_REVIEW_MODEL` |

Exit codes: `0` no blocking findings, `1` findings at or above `--fail-on`, `2` error (not a git repo, missing API key, API failure).

Lockfiles, minified files, source maps, snapshots and binary files are left out of the diff. Diffs over 120k characters are truncated with a warning.

## As a pre-push hook

```bash
cat > .git/hooks/pre-push <<'HOOK'
#!/bin/sh
exec claude-review --base origin/main --fail-on high
HOOK
chmod +x .git/hooks/pre-push
```

## In GitHub Actions

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: pip install git+https://github.com/venkata-kopparthi/claude-review.git
- run: claude-review --base origin/${{ github.base_ref }} --format markdown > review.md
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
- run: gh pr comment ${{ github.event.pull_request.number }} --body-file review.md
  env:
    GH_TOKEN: ${{ github.token }}
```

## How it works

The diff is sent with a system prompt that asks for blocking issues only, and the response is forced through a `report_findings` tool with a JSON schema, so the output is always structured (file, line, severity, message, suggestion) rather than free text that has to be parsed. Findings are validated and sorted by severity before printing.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

The tests use a temporary git repo and a fake API client, so they run offline and don't need an API key.

## Limitations

- Line numbers come from the model and are occasionally off by a line or two.
- Very large diffs are truncated rather than split into multiple requests.
- Only the diff is sent, so issues that depend on code outside the changed hunks can be missed.

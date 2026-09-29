import argparse
import os
import sys

from rich.console import Console

from . import __version__
from .git import GitError, get_diff
from .render import print_text, to_json, to_markdown
from .review import SEVERITIES, ReviewError, review_diff

DEFAULT_MODEL = "claude-sonnet-5"
MAX_DIFF_CHARS = 120_000


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="claude-review",
        description="Review your git changes with Claude before you push.",
    )
    p.add_argument(
        "--base",
        help="review everything since this branch (e.g. main) instead of staged changes",
    )
    p.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    p.add_argument(
        "--fail-on",
        choices=[*SEVERITIES, "never"],
        default="high",
        help="exit with code 1 if there is a finding at or above this severity (default: high)",
    )
    p.add_argument("--model", default=os.getenv("CLAUDE_REVIEW_MODEL", DEFAULT_MODEL))
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def should_fail(worst: str | None, threshold: str) -> bool:
    if worst is None or threshold == "never":
        return False
    return SEVERITIES.index(worst) <= SEVERITIES.index(threshold)


def make_client():
    import anthropic

    return anthropic.Anthropic()


def main(argv: list[str] | None = None, client=None) -> int:
    args = build_parser().parse_args(argv)
    err = Console(stderr=True)
    out = Console()

    try:
        diff = get_diff(args.base)
    except GitError as e:
        err.print(f"[red]git error:[/red] {e}")
        return 2

    if not diff.strip():
        where = f"since {args.base}" if args.base else "staged"
        err.print(f"Nothing to review: no {where} changes. Stage files with `git add` first.")
        return 0

    if len(diff) > MAX_DIFF_CHARS:
        err.print(
            f"[yellow]The diff is large ({len(diff):,} characters); "
            f"only the first {MAX_DIFF_CHARS:,} are reviewed.[/yellow]"
        )
        diff = diff[:MAX_DIFF_CHARS]

    if client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            err.print("[red]ANTHROPIC_API_KEY is not set.[/red]")
            return 2
        client = make_client()

    try:
        with err.status("Reviewing…"):
            review = review_diff(client, diff, args.model)
    except ReviewError as e:
        err.print(f"[red]{e}[/red]")
        return 2
    except Exception as e:  # network errors, auth errors, rate limits
        err.print(f"[red]Review failed:[/red] {e}")
        return 2

    if args.format == "json":
        print(to_json(review))
    elif args.format == "markdown":
        print(to_markdown(review), end="")
    else:
        print_text(review, out)

    return 1 if should_fail(review.worst(), args.fail_on) else 0


def main_entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    main_entry()

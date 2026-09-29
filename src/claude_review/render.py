import json
from dataclasses import asdict

from rich.console import Console
from rich.text import Text

from .review import Review

STYLES = {"high": "bold red", "medium": "yellow", "low": "cyan"}


def location(file: str, line: int | None) -> str:
    return f"{file}:{line}" if line else file


def print_text(review: Review, console: Console) -> None:
    if review.summary:
        console.print(Text(review.summary, style="dim"))
        console.print()
    if not review.findings:
        console.print("[green]No issues found.[/green]")
        return

    for f in review.findings:
        header = Text()
        header.append(f"{f.severity.upper():<7}", style=STYLES[f.severity])
        header.append(location(f.file, f.line), style="bold")
        console.print(header)
        console.print(f"       {f.message}")
        if f.suggestion:
            console.print(Text(f"       → {f.suggestion}", style="dim"))
        console.print()

    counts = {s: sum(f.severity == s for f in review.findings) for s in STYLES}
    console.print(", ".join(f"{n} {s}" for s, n in counts.items() if n))


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(review: Review) -> str:
    lines = ["## Code review", ""]
    if review.summary:
        lines += [f"_{review.summary}_", ""]
    if not review.findings:
        lines.append("No issues found.")
        return "\n".join(lines) + "\n"

    lines += ["| Severity | Location | Issue |", "| --- | --- | --- |"]
    for f in review.findings:
        issue = escape_cell(f.message)
        if f.suggestion:
            issue += f"<br>**Suggestion:** {escape_cell(f.suggestion)}"
        lines.append(f"| {f.severity} | `{location(f.file, f.line)}` | {issue} |")
    return "\n".join(lines) + "\n"


def to_json(review: Review) -> str:
    return json.dumps(
        {"summary": review.summary, "findings": [asdict(f) for f in review.findings]}, indent=2
    )

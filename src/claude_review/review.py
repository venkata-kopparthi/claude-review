from dataclasses import dataclass
from typing import Any, Protocol

SEVERITIES = ("high", "medium", "low")

SYSTEM_PROMPT = """You are reviewing a git diff as a senior engineer on the team.

Report only problems a careful reviewer would block or comment on: bugs, security issues, \
race conditions, data loss, broken error handling, missing input validation, and changes that \
contradict nearby code. Skip style nits a formatter or linter would catch, and do not praise \
the code.

For each finding, point at the file and the line number in the new version of the file. Keep \
the message to one or two sentences and, when it helps, include a concrete suggestion.

Severity:
- high: will cause incorrect behavior, a crash, or a security problem
- medium: likely bug or missing edge case
- low: worth a look, but not blocking

If the diff looks fine, report no findings."""

REPORT_TOOL = {
    "name": "report_findings",
    "description": "Report the review findings for the diff.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One sentence on what the change does.",
            },
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "severity": {"type": "string", "enum": list(SEVERITIES)},
                        "message": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["file", "severity", "message"],
                },
            },
        },
        "required": ["summary", "findings"],
    },
}


@dataclass
class Finding:
    file: str
    severity: str
    message: str
    line: int | None = None
    suggestion: str | None = None


@dataclass
class Review:
    summary: str
    findings: list[Finding]

    def worst(self) -> str | None:
        for sev in SEVERITIES:
            if any(f.severity == sev for f in self.findings):
                return sev
        return None


class MessagesClient(Protocol):
    @property
    def messages(self) -> Any: ...


class ReviewError(Exception):
    pass


def review_diff(client: MessagesClient, diff: str, model: str, max_tokens: int = 4096) -> Review:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[REPORT_TOOL],
        tool_choice={"type": "tool", "name": "report_findings"},
        messages=[{"role": "user", "content": f"<diff>\n{diff}\n</diff>"}],
    )
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None:
        raise ReviewError("The model did not return any findings. Try again.")
    return parse_review(block.input)


def parse_review(data: dict) -> Review:
    findings = []
    for raw in data.get("findings", []):
        severity = str(raw.get("severity", "low")).lower()
        if severity not in SEVERITIES:
            severity = "low"
        line = raw.get("line")
        findings.append(
            Finding(
                file=raw.get("file", "?"),
                severity=severity,
                message=raw.get("message", "").strip(),
                line=line if isinstance(line, int) and line > 0 else None,
                suggestion=(raw.get("suggestion") or "").strip() or None,
            )
        )
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings.sort(key=lambda f: (order[f.severity], f.file, f.line or 0))
    return Review(summary=data.get("summary", "").strip(), findings=findings)

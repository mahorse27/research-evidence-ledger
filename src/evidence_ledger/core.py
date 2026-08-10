"""Core data, validation, and rendering functions for evidence ledgers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
KINDS = (
    "literature_fact",
    "formal_inference",
    "hypothesis",
    "evidence_gap",
)
KIND_PREFIXES = {
    "literature_fact": "F",
    "formal_inference": "I",
    "hypothesis": "H",
    "evidence_gap": "G",
}
KIND_TITLES = {
    "literature_fact": "Literature facts",
    "formal_inference": "Formal inferences",
    "hypothesis": "Hypotheses",
    "evidence_gap": "Evidence gaps",
}
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class LedgerError(ValueError):
    """Raised when a ledger cannot be loaded or safely updated."""


@dataclass(frozen=True)
class AuditIssue:
    severity: str
    code: str
    message: str
    entry_id: str | None = None

    def format(self) -> str:
        location = f" [{self.entry_id}]" if self.entry_id else ""
        return f"{self.severity.upper()} {self.code}{location}: {self.message}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_ledger(title: str, description: str = "") -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise LedgerError("Project title cannot be empty.")
    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "title": title,
            "description": description.strip(),
            "created_at": now,
            "updated_at": now,
        },
        "entries": [],
    }


def load_ledger(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"Ledger not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(data, dict):
        raise LedgerError("Ledger root must be a JSON object.")
    return data


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    project = ledger.get("project")
    if isinstance(project, dict):
        project["updated_at"] = utc_now()
    payload = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def next_entry_id(entries: Iterable[dict[str, Any]], kind: str) -> str:
    if kind not in KIND_PREFIXES:
        raise LedgerError(f"Unknown entry kind: {kind}")
    prefix = KIND_PREFIXES[kind]
    maximum = 0
    pattern = re.compile(rf"^{prefix}-(\d+)$")
    for entry in entries:
        match = pattern.match(str(entry.get("id", "")))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return f"{prefix}-{maximum + 1:03d}"


def build_entry(
    entries: list[dict[str, Any]],
    *,
    kind: str,
    claim: str,
    citation: str = "",
    doi: str = "",
    url: str = "",
    basis: Iterable[str] = (),
    test_plan: Iterable[str] = (),
    resolution_plan: Iterable[str] = (),
    tags: Iterable[str] = (),
    notes: str = "",
) -> dict[str, Any]:
    if kind not in KINDS:
        raise LedgerError(f"Unknown entry kind: {kind}")
    source = {
        key: value.strip()
        for key, value in (("citation", citation), ("doi", doi), ("url", url))
        if value.strip()
    }
    return {
        "id": next_entry_id(entries, kind),
        "kind": kind,
        "claim": claim.strip(),
        "source": source,
        "basis": _clean_list(basis),
        "test_plan": _clean_list(test_plan),
        "resolution_plan": _clean_list(resolution_plan),
        "tags": _clean_list(tags),
        "notes": notes.strip(),
        "created_at": utc_now(),
    }


def audit_ledger(ledger: dict[str, Any]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    if ledger.get("schema_version") != SCHEMA_VERSION:
        issues.append(AuditIssue("error", "schema-version", f"Expected schema_version {SCHEMA_VERSION}."))

    project = ledger.get("project")
    if not isinstance(project, dict):
        issues.append(AuditIssue("error", "project-object", "Project metadata must be an object."))
    elif not str(project.get("title", "")).strip():
        issues.append(AuditIssue("error", "project-title", "Project title is required."))

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        issues.append(AuditIssue("error", "entries-list", "Entries must be a list."))
        return issues

    known_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            issues.append(AuditIssue("error", "entry-object", "Every entry must be an object."))
            continue
        entry_id = str(raw_entry.get("id", "")).strip()
        if not entry_id:
            issues.append(AuditIssue("error", "entry-id", "Entry ID is required."))
        elif entry_id in known_ids:
            duplicate_ids.add(entry_id)
        else:
            known_ids.add(entry_id)
    for entry_id in sorted(duplicate_ids):
        issues.append(AuditIssue("error", "duplicate-id", "Entry ID must be unique.", entry_id))

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        entry_id = str(raw_entry.get("id", "")).strip() or None
        kind = raw_entry.get("kind")
        claim = str(raw_entry.get("claim", "")).strip()
        if kind not in KINDS:
            issues.append(AuditIssue("error", "entry-kind", f"Kind must be one of: {', '.join(KINDS)}.", entry_id))
            continue
        if not claim:
            issues.append(AuditIssue("error", "entry-claim", "Claim text is required.", entry_id))

        source = raw_entry.get("source", {})
        if not isinstance(source, dict):
            issues.append(AuditIssue("error", "source-object", "Source must be an object.", entry_id))
            source = {}
        has_source = any(str(source.get(field, "")).strip() for field in ("citation", "doi", "url"))
        doi = str(source.get("doi", "")).strip()
        if doi and not DOI_PATTERN.match(doi):
            issues.append(AuditIssue("warning", "doi-format", "DOI does not match the expected 10.xxxx/suffix form.", entry_id))

        basis = _as_string_list(raw_entry.get("basis"), "basis", entry_id, issues)
        test_plan = _as_string_list(raw_entry.get("test_plan"), "test_plan", entry_id, issues)
        resolution_plan = _as_string_list(raw_entry.get("resolution_plan"), "resolution_plan", entry_id, issues)
        _as_string_list(raw_entry.get("tags"), "tags", entry_id, issues)

        if kind == "literature_fact" and not has_source:
            issues.append(AuditIssue("error", "fact-source", "Literature facts require a citation, DOI, or URL.", entry_id))
        if kind == "formal_inference" and not basis:
            issues.append(AuditIssue("error", "inference-basis", "Formal inferences require at least one basis entry ID.", entry_id))
        for basis_id in basis:
            if basis_id not in known_ids:
                issues.append(AuditIssue("error", "unknown-basis", f"Basis entry does not exist: {basis_id}.", entry_id))
            elif basis_id == entry_id:
                issues.append(AuditIssue("error", "self-basis", "An entry cannot cite itself as a basis.", entry_id))
        if kind == "hypothesis" and not test_plan:
            issues.append(AuditIssue("warning", "hypothesis-test", "Add a discriminating test plan.", entry_id))
        if kind == "evidence_gap" and not resolution_plan:
            issues.append(AuditIssue("warning", "gap-resolution", "Add a plan for resolving the evidence gap.", entry_id))

    return issues


def render_markdown(ledger: dict[str, Any]) -> str:
    project = ledger.get("project", {})
    title = str(project.get("title", "Untitled evidence ledger"))
    description = str(project.get("description", "")).strip()
    entries = ledger.get("entries", [])
    lines = [f"# {title}", ""]
    if description:
        lines.extend([description, ""])
    lines.extend(
        [
            f"- Schema version: `{ledger.get('schema_version', 'unknown')}`",
            f"- Updated: `{project.get('updated_at', 'unknown')}`",
            f"- Entries: `{len(entries) if isinstance(entries, list) else 0}`",
            "",
        ]
    )

    if not isinstance(entries, list):
        entries = []
    for kind in KINDS:
        matching = [entry for entry in entries if isinstance(entry, dict) and entry.get("kind") == kind]
        lines.extend([f"## {KIND_TITLES[kind]}", ""])
        if not matching:
            lines.extend(["_None recorded._", ""])
            continue
        for entry in matching:
            lines.extend(_render_entry(entry))

    issues = audit_ledger(ledger)
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    lines.extend(["## Audit status", "", f"Errors: **{errors}**. Warnings: **{warnings}**.", ""])
    if issues:
        lines.extend([f"- `{issue.code}`: {_escape_markdown(issue.message)}" for issue in issues])
        lines.append("")
    else:
        lines.extend(["The ledger passes all current audit rules.", ""])
    return "\n".join(lines)


def summarize(ledger: dict[str, Any]) -> dict[str, int]:
    counts = {kind: 0 for kind in KINDS}
    entries = ledger.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("kind") in counts:
                counts[entry["kind"]] += 1
    issues = audit_ledger(ledger)
    counts["errors"] = sum(issue.severity == "error" for issue in issues)
    counts["warnings"] = sum(issue.severity == "warning" for issue in issues)
    counts["total"] = sum(counts[kind] for kind in KINDS)
    return counts


def _clean_list(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _as_string_list(
    value: Any,
    field: str,
    entry_id: str | None,
    issues: list[AuditIssue],
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        issues.append(AuditIssue("error", f"{field}-list", f"{field} must be a list of strings.", entry_id))
        return []
    return [item.strip() for item in value if item.strip()]


def _render_entry(entry: dict[str, Any]) -> list[str]:
    entry_id = str(entry.get("id", "unknown"))
    claim = _escape_markdown(str(entry.get("claim", "")))
    lines = [f"### {entry_id}", "", claim, ""]
    source = entry.get("source", {})
    if isinstance(source, dict) and source:
        source_parts = [f"{key}: `{_escape_markdown(str(value))}`" for key, value in source.items() if value]
        if source_parts:
            lines.append("- Source: " + "; ".join(source_parts))
    for label, field in (
        ("Basis", "basis"),
        ("Test plan", "test_plan"),
        ("Resolution plan", "resolution_plan"),
        ("Tags", "tags"),
    ):
        values = entry.get(field, [])
        if isinstance(values, list) and values:
            lines.append(f"- {label}: " + "; ".join(_escape_markdown(str(value)) for value in values))
    notes = str(entry.get("notes", "")).strip()
    if notes:
        lines.append(f"- Notes: {_escape_markdown(notes)}")
    lines.extend([f"- Recorded: `{entry.get('created_at', 'unknown')}`", ""])
    return lines


def _escape_markdown(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")

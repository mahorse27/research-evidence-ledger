"""Command-line interface for Research Evidence Ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    KINDS,
    LedgerError,
    audit_ledger,
    build_entry,
    create_ledger,
    load_ledger,
    render_markdown,
    save_ledger,
    summarize,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-ledger",
        description="Keep research facts, inferences, hypotheses, and evidence gaps auditable.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create an empty evidence ledger.")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--description", default="")
    init_parser.add_argument("--force", action="store_true", help="Replace an existing ledger.")
    init_parser.set_defaults(handler=command_init)

    add_parser = subparsers.add_parser("add", help="Add one evidence entry.")
    add_parser.add_argument("path", type=Path)
    add_parser.add_argument("--kind", required=True, choices=KINDS)
    add_parser.add_argument("--claim", required=True)
    add_parser.add_argument("--citation", default="")
    add_parser.add_argument("--doi", default="")
    add_parser.add_argument("--url", default="")
    add_parser.add_argument("--basis", action="append", default=[])
    add_parser.add_argument("--test", dest="test_plan", action="append", default=[])
    add_parser.add_argument("--resolve", dest="resolution_plan", action="append", default=[])
    add_parser.add_argument("--tag", dest="tags", action="append", default=[])
    add_parser.add_argument("--notes", default="")
    add_parser.set_defaults(handler=command_add)

    validate_parser = subparsers.add_parser("validate", help="Audit a ledger and return a process-friendly exit code.")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--strict", action="store_true", help="Treat warnings as validation failures.")
    validate_parser.set_defaults(handler=command_validate)

    render_parser = subparsers.add_parser("render", help="Render an evidence ledger as Markdown.")
    render_parser.add_argument("path", type=Path)
    render_parser.add_argument("--output", "-o", type=Path)
    render_parser.set_defaults(handler=command_render)

    summary_parser = subparsers.add_parser("summary", help="Print machine-readable entry and audit counts.")
    summary_parser.add_argument("path", type=Path)
    summary_parser.set_defaults(handler=command_summary)
    return parser


def command_init(args: argparse.Namespace) -> int:
    if args.path.exists() and not args.force:
        raise LedgerError(f"Refusing to replace existing ledger: {args.path}. Use --force to replace it.")
    ledger = create_ledger(args.title, args.description)
    save_ledger(args.path, ledger)
    print(f"Created {args.path}")
    return 0


def command_add(args: argparse.Namespace) -> int:
    ledger = load_ledger(args.path)
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise LedgerError("Cannot add an entry until the ledger entries field is repaired.")
    entry = build_entry(
        entries,
        kind=args.kind,
        claim=args.claim,
        citation=args.citation,
        doi=args.doi,
        url=args.url,
        basis=args.basis,
        test_plan=args.test_plan,
        resolution_plan=args.resolution_plan,
        tags=args.tags,
        notes=args.notes,
    )
    candidate = {**ledger, "entries": [*entries, entry]}
    entry_errors = [issue for issue in audit_ledger(candidate) if issue.severity == "error" and issue.entry_id == entry["id"]]
    if entry_errors:
        details = "\n".join(issue.format() for issue in entry_errors)
        raise LedgerError(f"Entry failed validation and was not saved:\n{details}")
    entries.append(entry)
    save_ledger(args.path, ledger)
    print(f"Added {entry['id']} ({entry['kind']})")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    ledger = load_ledger(args.path)
    issues = audit_ledger(ledger)
    for issue in issues:
        print(issue.format())
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    print(f"Audit complete: {errors} error(s), {warnings} warning(s).")
    return 1 if errors or (args.strict and warnings) else 0


def command_render(args: argparse.Namespace) -> int:
    ledger = load_ledger(args.path)
    markdown = render_markdown(ledger)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Rendered {args.output}")
    else:
        print(markdown, end="")
    return 0


def command_summary(args: argparse.Namespace) -> int:
    print(json.dumps(summarize(load_ledger(args.path)), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

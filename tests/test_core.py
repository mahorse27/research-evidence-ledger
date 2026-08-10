import json

from evidence_ledger.core import (
    audit_ledger,
    build_entry,
    create_ledger,
    render_markdown,
    summarize,
)


def test_empty_ledger_is_valid():
    ledger = create_ledger("Example")
    assert audit_ledger(ledger) == []
    assert summarize(ledger)["total"] == 0


def test_facts_need_a_source():
    ledger = create_ledger("Example")
    ledger["entries"].append(build_entry(ledger["entries"], kind="literature_fact", claim="A claim"))
    issues = audit_ledger(ledger)
    assert any(issue.code == "fact-source" and issue.severity == "error" for issue in issues)


def test_inference_requires_existing_basis():
    ledger = create_ledger("Example")
    ledger["entries"].append(
        build_entry(
            ledger["entries"],
            kind="formal_inference",
            claim="An inference",
            basis=["F-404"],
        )
    )
    issues = audit_ledger(ledger)
    assert any(issue.code == "unknown-basis" for issue in issues)


def test_hypothesis_basis_must_also_exist():
    ledger = create_ledger("Example")
    ledger["entries"].append(
        build_entry(
            ledger["entries"],
            kind="hypothesis",
            claim="A hypothesis",
            basis=["I-404"],
            test_plan=["Run a control"],
        )
    )
    issues = audit_ledger(ledger)
    assert any(issue.code == "unknown-basis" for issue in issues)


def test_hypothesis_and_gap_require_action_plans():
    ledger = create_ledger("Example")
    ledger["entries"].append(build_entry(ledger["entries"], kind="hypothesis", claim="Testable idea"))
    ledger["entries"].append(build_entry(ledger["entries"], kind="evidence_gap", claim="Missing evidence"))
    issues = audit_ledger(ledger)
    assert any(issue.code == "hypothesis-test" for issue in issues)
    assert any(issue.code == "gap-resolution" for issue in issues)


def test_render_includes_sections_and_audit_status():
    ledger = create_ledger("Rendered")
    ledger["entries"].append(
        build_entry(
            ledger["entries"],
            kind="literature_fact",
            claim="A sourced claim",
            doi="10.1234/example",
            tags=["demo"],
        )
    )
    output = render_markdown(ledger)
    assert "# Rendered" in output
    assert "## Literature facts" in output
    assert "10.1234/example" in output
    assert "## Audit status" in output


def test_json_round_trip_shape():
    ledger = create_ledger("Round trip")
    ledger["entries"].append(
        build_entry(ledger["entries"], kind="literature_fact", claim="Claim", citation="Example 2026")
    )
    encoded = json.dumps(ledger)
    decoded = json.loads(encoded)
    assert summarize(decoded)["literature_fact"] == 1

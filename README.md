# Research Evidence Ledger

[![CI](https://github.com/mahorse27/research-evidence-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/mahorse27/research-evidence-ledger/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2F6F4E)](LICENSE)

Research notes often mix four different things: what a source actually reports, what follows formally from those reports, what is still a hypothesis, and what evidence is missing. **Research Evidence Ledger** is a small, dependency-free Python CLI that keeps those states separate and makes the provenance auditable.

## Why this exists

The ledger is designed for chemistry, materials science, and other evidence-heavy work where a polished paragraph can accidentally turn a plausible mechanism into an apparent fact. Every entry has a stable ID, an evidence kind, optional source metadata, and an explicit plan for testing or resolving uncertainty.

## Quick start

```bash
python -m pip install -e .
evidence-ledger init ledger.json --title "My project"
evidence-ledger add ledger.json --kind literature_fact --claim "The paper reports ..." --doi 10.1234/example
evidence-ledger add ledger.json --kind formal_inference --claim "This implies ..." --basis F-001
evidence-ledger add ledger.json --kind hypothesis --claim "A testable possibility ..." --test "Run the discriminating control"
evidence-ledger add ledger.json --kind evidence_gap --claim "Still unknown ..." --resolve "Collect the missing measurement"
evidence-ledger validate ledger.json --strict
evidence-ledger render ledger.json --output ledger.md
evidence-ledger summary ledger.json
```

The bundled [demo ledger](examples/demo-ledger.json) shows all four entry types. A machine-readable [JSON Schema](schema/evidence-ledger.schema.json) is included for editor integration and downstream validation.

## Evidence model

| Kind | Meaning | Minimum requirement |
| --- | --- | --- |
| `literature_fact` | A claim directly supported by a cited source | Citation, DOI, or URL |
| `formal_inference` | A conclusion derived from recorded entries | Existing basis IDs |
| `hypothesis` | A proposal that is not yet established | Recommended discriminating test plan |
| `evidence_gap` | An unresolved limitation or missing observation | Recommended resolution plan |

`validate --strict` fails on errors and warnings, which makes it suitable for CI. The validator never decides whether a scientific claim is true; it checks whether the claim's evidence status and provenance are explicit.

## Development

```bash
python -m pip install -e .
python -m pytest
```

The project intentionally keeps the runtime dependency-free. Contributions that add parsers or integrations should preserve the JSON schema and include fixtures plus tests.

## Roadmap

- Editor completion hints and schema-aware examples for common IDEs.
- BibTeX and Crossref metadata import with source provenance preserved.
- GitHub Actions report that comments audit findings on pull requests.
- Optional adapters for Markdown front matter and common lab-notebook exports.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md), open an issue describing the evidence workflow you need, and include a minimal fixture for new validation rules.

Release history is recorded in [CHANGELOG.md](CHANGELOG.md). Researchers may cite a specific release using the metadata in [CITATION.cff](CITATION.cff).

## Security and privacy

The CLI is local-first and does not upload ledger contents. Do not commit unpublished results, credentials, API keys, or personally identifying information. See [SECURITY.md](SECURITY.md) for reporting guidance.

## License

MIT. See [LICENSE](LICENSE).

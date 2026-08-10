# Contributing

Thanks for helping make evidence status explicit.

## Pull requests

1. Keep changes focused and explain the user-facing behavior.
2. Add or update tests for every validation rule or CLI change.
3. Run `python -m pytest` and `python -m compileall -q src` locally.
4. Keep the JSON schema backwards-compatible where possible. If a breaking change is necessary, increment `schema_version` and document a migration path.

## Scientific claims

Do not present an unsupported result as a fact in examples or documentation. Use `formal_inference`, `hypothesis`, or `evidence_gap` when the evidence status is not direct.

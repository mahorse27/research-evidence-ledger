import json
import subprocess
import sys
from pathlib import Path


def run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "evidence_ledger", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_init_add_validate_render_summary(tmp_path: Path):
    repo = Path(__file__).parents[1]
    ledger = tmp_path / "ledger.json"
    rendered = tmp_path / "ledger.md"

    result = run_cli(repo, "init", str(ledger), "--title", "CLI demo")
    assert result.returncode == 0, result.stderr
    result = run_cli(
        repo,
        "add",
        str(ledger),
        "--kind",
        "literature_fact",
        "--claim",
        "A sourced result",
        "--citation",
        "Example et al. (2026)",
    )
    assert result.returncode == 0, result.stderr
    result = run_cli(repo, "validate", str(ledger), "--strict")
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_cli(repo, "render", str(ledger), "--output", str(rendered))
    assert result.returncode == 0, result.stderr
    assert "## Literature facts" in rendered.read_text(encoding="utf-8")
    result = run_cli(repo, "summary", str(ledger))
    assert json.loads(result.stdout)["total"] == 1

import subprocess
import sys
from pathlib import Path

from tools.generate_conformance_report import (
    REPO_ROOT,
    display_output_path,
    resolve_output_path,
)

ROOT = Path(__file__).resolve().parents[2]


def _run(mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fix_refs.py"), mode],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_specification_references_are_valid() -> None:
    result = _run("--verify")
    assert result.returncode == 0, result.stderr


def test_invariant_declarations_use_rfc2119_capitalization() -> None:
    result = _run("--rfc2119")
    assert result.returncode == 0, result.stderr


def test_conformance_output_paths_support_ci_relative_and_external_targets(tmp_path) -> None:
    relative = resolve_output_path(Path("conformance-report-ci.md"))
    external = tmp_path / "report.md"

    assert relative == REPO_ROOT / "conformance-report-ci.md"
    assert display_output_path(relative) == Path("conformance-report-ci.md")
    assert resolve_output_path(external) == external
    assert display_output_path(external) == external

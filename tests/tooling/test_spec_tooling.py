import subprocess
import sys
from pathlib import Path

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

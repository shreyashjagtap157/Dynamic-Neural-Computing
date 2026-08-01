import json
import os
import subprocess
import sys
from pathlib import Path

from dnc.ir.serialization import DNWIRSerializer

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "dnc", *args],
        cwd=ROOT,
        env=environment,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def _context_document() -> dict:
    return {
        "tenant_id": "tenant-a",
        "permissions": ["provider:invoke"],
        "isolation_grade": "I3_RECORDED_EXTERNALS",
        "region": "IN",
        "device": "cpu",
        "runtime": "python",
        "capabilities": ["provider-recording"],
        "trust_zone": "enclave",
        "confidential_compute": True,
    }


def test_cli_validate_inspect_and_project_plain_graph(tmp_path, plain_graph) -> None:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(DNWIRSerializer.to_json(plain_graph), encoding="utf-8")

    validated = _run("graph", "validate", str(graph_path))
    inspected = _run("graph", "inspect", str(graph_path))
    projected = _run("graph", "project", str(graph_path))

    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["valid"] is True
    assert inspected.returncode == 0, inspected.stderr
    assert json.loads(inspected.stdout)["graph_id"] == "sdk-plain"
    assert projected.returncode == 0, projected.stderr
    assert json.loads(projected.stdout)["topological_order"] == ["plain"]


def test_cli_governed_graph_fails_closed_without_context(
    tmp_path,
    governed_graph,
) -> None:
    graph_path = tmp_path / "governed.json"
    context_path = tmp_path / "context.json"
    graph_path.write_text(DNWIRSerializer.to_json(governed_graph), encoding="utf-8")
    context_path.write_text(json.dumps(_context_document()), encoding="utf-8")

    missing = _run("graph", "validate", str(graph_path))
    admitted = _run(
        "graph",
        "validate",
        str(graph_path),
        "--context",
        str(context_path),
    )

    assert missing.returncode == 1
    assert json.loads(missing.stdout)["errors"][0]["code"] == "CTX_REQUIRED"
    assert admitted.returncode == 0, admitted.stderr
    assert json.loads(admitted.stdout)["execution_admissible"] is True


def test_cli_supports_stdin_and_output_file(tmp_path, plain_graph) -> None:
    output_path = tmp_path / "projection.json"
    completed = _run(
        "graph",
        "project",
        "-",
        "--output",
        str(output_path),
        input_text=DNWIRSerializer.to_json(plain_graph),
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["graph_id"] == "sdk-plain"


def test_cli_reports_machine_readable_failures(tmp_path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")

    completed = _run("graph", "inspect", str(malformed))

    assert completed.returncode == 1
    error = json.loads(completed.stderr)["error"]
    assert error["code"] == "DNCValidationError"
    assert "valid JSON" in error["message"]

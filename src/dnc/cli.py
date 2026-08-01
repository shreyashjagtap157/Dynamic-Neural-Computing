"""Dependency-free command line interface for Generic DNC-IR operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from dnc.kernel.errors import DNCError, DNCValidationError
from dnc.sdk import DNCSDK, execution_context_from_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dnc", description="Dynamic Neural Computing CLI")
    subcommands = parser.add_subparsers(dest="resource", required=True)
    graph = subcommands.add_parser("graph", help="work with Generic DNC-IR graphs")
    graph_commands = graph.add_subparsers(dest="operation", required=True)

    validate = graph_commands.add_parser("validate", help="validate a graph and its governance")
    _add_input_context_arguments(validate)
    validate.add_argument(
        "--structural-only",
        action="store_true",
        help="do not require an execution context for governed graphs",
    )

    inspect = graph_commands.add_parser("inspect", help="inspect graph structure and admission")
    _add_input_context_arguments(inspect)

    project = graph_commands.add_parser("project", help="project a graph to an executable DAG")
    _add_input_context_arguments(project)
    project.add_argument("--output", "-o", default="-", help="output JSON path or '-' for stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sdk = DNCSDK()
    try:
        payload = _read_text(args.input)
        context = _read_context(args.context)
        if args.operation == "validate":
            result = sdk.validate_graph(
                payload,
                context=context,
                require_execution_context=not args.structural_only,
            )
            _write_json(result.to_dict(), "-")
            return 0 if result.valid else 1
        if args.operation == "inspect":
            _write_json(sdk.inspect_graph(payload, context=context), "-")
            return 0
        if args.operation == "project":
            _write_json(sdk.project_graph(payload, context=context).to_dict(), args.output)
            return 0
        raise AssertionError(f"unhandled operation: {args.operation}")
    except (DNCError, OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
        _write_error(error)
        return 1


def _add_input_context_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", help="input graph JSON path or '-' for stdin")
    parser.add_argument("--context", help="execution-context JSON path")


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _read_context(path: str | None):
    if path is None:
        return None
    try:
        document = json.loads(_read_text(path))
    except json.JSONDecodeError as error:
        raise DNCValidationError("execution context MUST be valid JSON") from error
    return execution_context_from_dict(document)


def _write_json(document: dict[str, Any], path: str) -> None:
    payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if path == "-":
        sys.stdout.write(payload)
    else:
        Path(path).write_text(payload, encoding="utf-8")


def _write_error(error: Exception) -> None:
    payload = {
        "error": {
            "code": type(error).__name__,
            "message": str(error),
        }
    }
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")

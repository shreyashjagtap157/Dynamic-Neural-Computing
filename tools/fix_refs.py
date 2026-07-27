"""Validate specification references and normative invariant wording.

The historical tool was referenced by CI but absent. This replacement performs
non-destructive validation; it never rewrites specifications implicitly.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
LOWER_NORMATIVE = re.compile(r"\b(must|must not|shall|shall not|should|should not|may)\b", re.I)
INVARIANT_LINE = re.compile(r"^\s*\*\*INV-[A-Z0-9-]+")


def _layer(path: Path) -> int | None:
    for part in path.parts:
        match = re.fullmatch(r"layer-(\d+)[-\w]*", part)
        if match:
            return int(match.group(1))
    return None


def verify_references() -> list[str]:
    errors: list[str] = []
    for document in sorted(SPECS.rglob("*.md")):
        text = document.read_text(encoding="utf-8")
        source_layer = _layer(document.relative_to(SPECS))
        for line_number, line in enumerate(text.splitlines(), 1):
            for target_text in MARKDOWN_LINK.findall(line):
                if target_text.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target_path_text = target_text.split("#", 1)[0]
                if not target_path_text:
                    continue
                target = (document.parent / target_path_text).resolve()
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    errors.append(f"{document}:{line_number}: reference escapes repository: {target_text}")
                    continue
                if not target.exists():
                    errors.append(f"{document}:{line_number}: missing reference: {target_text}")
                    continue
                target_layer = _layer(target.relative_to(SPECS)) if target.is_relative_to(SPECS) else None
                if (
                    source_layer is not None
                    and target_layer is not None
                    and target_layer > source_layer
                ):
                    errors.append(
                        f"{document}:{line_number}: PR-4 violation: layer {source_layer} "
                        f"references higher layer {target_layer}: {target_text}"
                    )
    return errors


def verify_rfc2119() -> list[str]:
    """Require RFC 2119 capitalization in invariant declaration lines.

    Explanatory prose and research questions intentionally use ordinary-language
    modal verbs, so only declarations beginning with an invariant identifier are
    normative for this check.
    """
    errors: list[str] = []
    for document in sorted(SPECS.rglob("*.md")):
        for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            if not INVARIANT_LINE.match(line):
                continue
            for match in LOWER_NORMATIVE.finditer(line):
                token = match.group(0)
                if token != token.upper():
                    errors.append(
                        f"{document}:{line_number}: PR-7 normative keyword must be uppercase: {token}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="validate local references and PR-4")
    parser.add_argument("--rfc2119", action="store_true", help="validate PR-7 normative wording")
    args = parser.parse_args()
    checks = []
    if args.verify or not args.rfc2119:
        checks.extend(verify_references())
    if args.rfc2119:
        checks.extend(verify_rfc2119())
    if checks:
        print("\n".join(checks), file=sys.stderr)
        return 1
    mode = "RFC 2119" if args.rfc2119 and not args.verify else "reference"
    print(f"Specification {mode} validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Freeze all DNC spec documents from Draft to Baseline v1.0.

Per conformance-model.md Section 2: Architecture v1.0 is frozen and all normative
documents MUST be in Frozen state before implementation is declared complete.

Usage: python tools/freeze_spec.py --dry-run  # preview changes
       python tools/freeze_spec.py            # apply changes
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SPEC_ROOT = Path(__file__).parent.parent / "specs"

VERSION_REPLACEMENTS = [
    ("Draft DR-1", "Baseline v1.0"),
    ("Draft DR-2", "Baseline v1.0"),
    ("Architecture v1.0 Draft", "Architecture v1.0"),
]

STATE_REPLACEMENT = ("Draft", "Frozen")


def freeze_file(filepath: Path, dry_run: bool = False) -> list:
    changes = []
    content = filepath.read_text(encoding="utf-8")
    new_content = content

    for old_ver, new_ver in VERSION_REPLACEMENTS:
        if old_ver in new_content:
            new_content = new_content.replace(f"| Version | {old_ver} |", f"| Version | {new_ver} |")
            changes.append(f"  {filepath.name}: '{old_ver}' -> '{new_ver}'")

    if "Draft DR-1" not in content and "Draft DR-2" not in content and "Architecture v1.0 Draft" not in content:
        pass
    else:
        pass

    old_state = "| State | Draft |"
    new_state = "| State | Frozen |"
    if old_state in new_content:
        new_content = new_content.replace(old_state, new_state)
        changes.append(f"  {filepath.name}: State 'Draft' -> 'Frozen'")

    amend_section_match = re.search(r"(### Section 6 — Amendment Log.*?\n)(\|.*?\|.*?\|.*?\|.*?\|)\n(\n|$)",
                                    new_content, re.DOTALL)
    if amend_section_match:
        existing = amend_section_match.group(2)
        new_amend = f"""{existing}
| FRZ-001 | {filepath.name} | 2026-07-12 | Frozen to Baseline v1.0. All draft content is now frozen per conformance-model.md Section 2. | No |
"""
        new_content = new_content[:amend_section_match.start(3)] + new_amend + new_content[amend_section_match.start(3):]
        changes.append(f"  {filepath.name}: Added FRZ-001 amendment log entry")

    if new_content != content and not dry_run:
        filepath.write_text(new_content, encoding="utf-8")

    return changes


def main(dry_run: bool = False) -> None:
    action = "DRY RUN (no changes)" if dry_run else "APPLYING CHANGES"
    print(f"\n=== DNC SPEC FREEZE: {action} ===\n")

    md_files = sorted(SPEC_ROOT.glob("**/*.md"))
    total_changes = 0

    for filepath in md_files:
        if "README" in filepath.name:
            continue
        changes = freeze_file(filepath, dry_run=dry_run)
        if changes:
            for c in changes:
                print(c)
            total_changes += len(changes)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}{total_changes} changes {'would be' if dry_run else ''} made to {len(list(SPEC_ROOT.glob('**/*.md')))} spec files.")

    if dry_run:
        print("\nRun without --dry-run to apply these changes.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
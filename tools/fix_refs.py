#!/usr/bin/env python3
"""
Fix cross-references in DNC specification files.

Updates relative paths in markdown files to point to the correct layer-relative location.
Also supports verifying PR-4 compliance (no upward references).
"""

import os
import re
import argparse

SPECS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'specs')
FILE_LAYERS = {
    'specification-foundation.md': 'layer-0-foundation',
    'core-terminology.md': 'layer-1-terminology',
    'runtime-invariants.md': 'layer-2-invariants',
    'formal-model.md': 'layer-3-execution',
    'control-loop.md': 'layer-3-execution',
    'state-management.md': 'layer-3-execution',
    'module-lifecycle.md': 'layer-4-mechanisms',
    'planner-pipeline.md': 'layer-4-mechanisms',
    'scheduler.md': 'layer-4-mechanisms',
    'cost-semantics.md': 'layer-4-mechanisms',
    'provenance-model.md': 'layer-5-observability',
    'failure-taxonomy.md': 'layer-5-observability',
    'evaluation-suite.md': 'layer-5-observability',
    'continual-learning.md': 'layer-6-evolution',
    'mvp-roadmap.md': 'layer-6-evolution',
    'distributed-handoff-protocol.md': 'layer-7-distributed',
}

LAYER_FILES = {
    'layer-0-foundation': ['specification-foundation.md'],
    'layer-1-terminology': ['core-terminology.md'],
    'layer-2-invariants': ['runtime-invariants.md'],
    'layer-3-execution': ['formal-model.md', 'control-loop.md', 'state-management.md'],
    'layer-4-mechanisms': ['module-lifecycle.md', 'planner-pipeline.md', 'scheduler.md', 'cost-semantics.md'],
    'layer-5-observability': ['provenance-model.md', 'failure-taxonomy.md', 'evaluation-suite.md'],
    'layer-6-evolution': ['continual-learning.md', 'mvp-roadmap.md'],
    'layer-7-distributed': ['distributed-handoff-protocol.md'],
}

LAYER_NUMBERS = {
    'layer-0-foundation': 0,
    'layer-1-terminology': 1,
    'layer-2-invariants': 2,
    'layer-3-execution': 3,
    'layer-4-mechanisms': 4,
    'layer-5-observability': 5,
    'layer-6-evolution': 6,
    'layer-7-distributed': 7,
}

# LAYER_INVARIANTS removed — stale, misleading; tool verifies file-to-file
# cross-references only, not invariant identifier consistency


def get_relative_path(from_layer: str, from_filename: str, to_layer: str, to_filename: str) -> str:
    from_layer_num = LAYER_NUMBERS.get(from_layer, 0)
    to_layer_num = LAYER_NUMBERS.get(to_layer, 0)
    levels = abs(from_layer_num - to_layer_num)
    return '../' * levels + f'{to_layer}/{to_filename}'


def process_file(filepath: str, filename: str, layer: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    updated_lines = []
    updated = False

    for line in lines:
        for match in re.finditer(r'`([a-z][-a-z]*\.md)`', line):
            target_filename = match.group(1)
            if target_filename == filename:
                continue

            target_layer = FILE_LAYERS.get(target_filename)
            if target_layer is None:
                continue

            relative_path = get_relative_path(layer, filename, target_layer, target_filename)
            old_ref = f'`{target_filename}`'
            new_ref = f'`{relative_path}`'

            if old_ref in line:
                line = line.replace(old_ref, new_ref)
                updated = True

        updated_lines.append(line)

    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))

    return updated


def verify_pr4_compliance():
    """Verify every cross-reference in spec files points to a lower layer."""
    violations = []

    for layer_dir, files in LAYER_FILES.items():
        source_layer_num = LAYER_NUMBERS.get(layer_dir)
        for filename in files:
            filepath = os.path.join(SPECS_DIR, layer_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            current_filename = os.path.basename(filepath)

            for line_no, line in enumerate(content.split('\n'), 1):
                for match in re.finditer(r'`([a-z][-a-z]*\.md)`', line):
                    target_filename = match.group(1)
                    target_layer = FILE_LAYERS.get(target_filename)

                    if target_layer is None:
                        continue

                    target_layer_num = LAYER_NUMBERS.get(target_layer, 999)

                    if target_layer_num > source_layer_num:
                        violations.append(f"  VIOLATION in {filepath}:{line_no}: "
                                        f"{current_filename} (L{source_layer_num}) -> "
                                        f"{target_filename} (L{target_layer_num}) "
                                        f"[points UPWARD to higher layer]")

    if violations:
        print("\n=== PR-4 VIOLATIONS FOUND ===")
        for v in violations:
            print(v)
        print(f"\nTotal violations: {len(violations)}")
        return False
    else:
        print("\n=== PR-4 COMPLIANCE: PASSED ===")
        print("All cross-references point to lower-or-equal layers.")
        return True


def verify_rfc2119_compliance():
    """Verify every normative statement has an RFC 2119 keyword."""
    normative_violations = []
    docs_scanned = 0

    for layer_dir, files in LAYER_FILES.items():
        for filename in files:
            filepath = os.path.join(SPECS_DIR, layer_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            docs_scanned += 1

            for line_no, line in enumerate(content.split('\n'), 1):
                stripped = line.strip()
                if stripped.startswith('```') or stripped.startswith('|') or stripped.startswith('#') or stripped.startswith('*'):
                    continue
                if ('**Statement**' in line or '**Definition**' in line or '**Note**' in line) and len(stripped) > 10:
                    context = '\n'.join(content.split('\n')[line_no-1:line_no+5])
                    has_keyword = any(kw in context.upper() for kw in ['MUST', 'SHALL', 'SHOULD', 'MAY', 'REQUIRED', 'RECOMMENDED'])
                    if not has_keyword and '*' not in stripped[:2]:
                        normative_violations.append(f"  RFC2119 in {filepath}:{line_no}: {stripped[:80]}...")

    if normative_violations:
        print(f"\n=== RFC 2119 VIOLATIONS FOUND ({len(normative_violations)}) ===")
        for v in normative_violations[:20]:
            print(v)
        if len(normative_violations) > 20:
            print(f"  ... and {len(normative_violations) - 20} more")
        return False
    else:
        print(f"\n=== RFC 2119 COMPLIANCE: PASSED ({docs_scanned} docs scanned) ===")
        return True


def main():
    parser = argparse.ArgumentParser(description='Fix cross-references in DNC spec files, verify PR-4 compliance, or check RFC 2119 keyword discipline.')
    parser.add_argument('--verify', action='store_true', help='Verify PR-4 compliance without modifying files')
    parser.add_argument('--rfc2119', action='store_true', help='Check RFC 2119 keyword discipline')
    args = parser.parse_args()

    if args.verify or args.rfc2119:
        if args.verify:
            print('Running PR-4 compliance verification...')
            verify_pr4_compliance()
        if args.rfc2119:
            print('Running RFC 2119 keyword discipline check...')
            verify_rfc2119_compliance()
        return

    files_updated = 0
    for layer, filenames in LAYER_FILES.items():
        for filename in filenames:
            filepath = os.path.join(SPECS_DIR, layer, filename)
            if os.path.exists(filepath):
                if process_file(filepath, filename, layer):
                    files_updated += 1
                    print(f'Updated: {layer}/{filename}')

    print(f'\nTotal files updated: {files_updated}')


if __name__ == '__main__':
    main()
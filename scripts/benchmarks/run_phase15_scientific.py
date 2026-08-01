"""Generate the maintained Phase 15 controlled hidden-campaign artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dnc.cognition.canonical import canonical_data
from dnc.evaluation.reference_campaign import run_reference_campaign


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evaluation/artifacts/phase15-reference-campaign.json"),
    )
    args = parser.parse_args()
    artifact = run_reference_campaign()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(canonical_data(artifact), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({artifact.evidence_grade}, {artifact.fingerprint})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

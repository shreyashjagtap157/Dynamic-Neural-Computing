# Repository Scripts

- `audits/`: maintained, release-relevant system audits.
- `benchmarks/`: maintained benchmark harnesses, pilots, diagnostics, and campaigns.
- `legacy/`: historical phase and diagnostic entry points retained for provenance.

The authoritative automated gate is `pytest`; scripts are supplemental. Production
library code must never import from this directory.

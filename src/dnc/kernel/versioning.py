"""Version identifiers and compatibility policy for DNC Phase 1."""

DNC_IR_SCHEMA_ID = "dnc.ir.structural_graph"
DNC_IR_SCHEMA_VERSION = "1.1.0"
KERNEL_COMPATIBILITY_VERSION = "2026.07.phase1"
COMPATIBILITY_POLICY_VERSION = "1"


def schema_header() -> dict[str, str]:
    """Return canonical schema metadata for serialized DNC-IR graphs."""

    return {
        "schema_id": DNC_IR_SCHEMA_ID,
        "schema_version": DNC_IR_SCHEMA_VERSION,
        "compatibility_version": KERNEL_COMPATIBILITY_VERSION,
    }

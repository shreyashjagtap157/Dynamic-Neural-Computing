from dnc.kernel import (
    DNCError,
    DNCValidationError,
    DNC_IR_SCHEMA_ID,
    DNC_IR_SCHEMA_VERSION,
    KERNEL_COMPATIBILITY_VERSION,
)
from dnc.kernel.versioning import schema_header


def test_schema_header_exposes_version_identifiers() -> None:
    header = schema_header()

    assert header["schema_id"] == DNC_IR_SCHEMA_ID
    assert header["schema_version"] == DNC_IR_SCHEMA_VERSION
    assert header["compatibility_version"] == KERNEL_COMPATIBILITY_VERSION


def test_error_taxonomy_uses_common_base_class() -> None:
    assert issubclass(DNCValidationError, DNCError)

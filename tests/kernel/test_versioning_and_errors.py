import pytest

from dnc.kernel import (
    DNCError,
    DNCValidationError,
    DNC_IR_SCHEMA_ID,
    DNC_IR_SCHEMA_VERSION,
    KERNEL_COMPATIBILITY_VERSION,
)
from dnc.kernel.versioning import schema_header
from dnc.system import DNCSystem, DNCSystemConfig, ReferenceExecutionCore


def test_schema_header_exposes_version_identifiers() -> None:
    header = schema_header()

    assert header["schema_id"] == DNC_IR_SCHEMA_ID
    assert header["schema_version"] == DNC_IR_SCHEMA_VERSION
    assert header["compatibility_version"] == KERNEL_COMPATIBILITY_VERSION


def test_error_taxonomy_uses_common_base_class() -> None:
    assert issubclass(DNCValidationError, DNCError)


def test_production_mode_rejects_unapproved_synthetic_execution() -> None:
    with pytest.raises(ValueError, match="explicit non-synthetic"):
        DNCSystem(config=DNCSystemConfig(production_mode=True))
    with pytest.raises(ValueError, match="synthetic reference execution"):
        DNCSystem(
            config=DNCSystemConfig(production_mode=True),
            execution_core=ReferenceExecutionCore(),
        )

    approved = DNCSystem(
        config=DNCSystemConfig(production_mode=True, allow_synthetic_execution=True),
        execution_core=ReferenceExecutionCore(),
    )
    assert isinstance(approved.execution_core, ReferenceExecutionCore)

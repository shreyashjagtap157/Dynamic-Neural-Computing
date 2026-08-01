import pytest

from dnc.ir.contracts import (
    ExecutionContext,
    IdempotencyContract,
    IdempotencyMode,
    PlacementContract,
    SecurityContract,
    SideEffectContract,
)
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    UnitContract,
    VisibilityDimension,
)
from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass


def _unit(unit_id: str, contract: UnitContract | None = None) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
        contract=contract or UnitContract(),
    )


@pytest.fixture
def plain_graph() -> StructuralGraph:
    return StructuralGraph(
        GraphID("sdk-plain"),
        units={"plain": _unit("plain")},
        metadata={"purpose": "sdk-test"},
    )


@pytest.fixture
def governed_graph() -> StructuralGraph:
    contract = UnitContract(
        idempotency=IdempotencyContract(
            IdempotencyMode.KEY_REQUIRED,
            key_field="request_id",
        ),
        side_effects=SideEffectContract(
            SideEffectClass.IRREVERSIBLE,
            frozenset({EffectType.PROVIDER_CALL}),
            minimum_isolation=IsolationGrade.I3_RECORDED_EXTERNALS,
        ),
        placement=PlacementContract(
            allowed_regions=frozenset({"IN"}),
            allowed_devices=frozenset({"cpu"}),
            allowed_runtimes=frozenset({"python"}),
            required_capabilities=frozenset({"provider-recording"}),
        ),
        security=SecurityContract(
            tenant_id="tenant-a",
            required_permissions=frozenset({"provider:invoke"}),
            allowed_residencies=frozenset({"IN"}),
            trust_zone="enclave",
            accepted_trust_zones=frozenset({"enclave"}),
            confidential_compute_required=True,
        ),
    )
    return StructuralGraph(
        GraphID("sdk-governed"),
        units={"governed": _unit("governed", contract)},
    )


@pytest.fixture
def execution_context() -> ExecutionContext:
    return ExecutionContext(
        tenant_id="tenant-a",
        permissions=frozenset({"provider:invoke"}),
        isolation_grade=IsolationGrade.I3_RECORDED_EXTERNALS,
        region="IN",
        device="cpu",
        runtime="python",
        capabilities=frozenset({"provider-recording"}),
        trust_zone="enclave",
        confidential_compute=True,
    )

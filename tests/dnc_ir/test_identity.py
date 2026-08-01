import pytest
from dnc.ir.identity import (
    GraphID,
    GraphVersion,
    IdentityRegistry,
    InstanceID,
    MutationID,
    TransactionID,
    UnitID,
)

def test_identity_immutability():
    uid = UnitID("unit_test_1")
    assert str(uid) == "unit_test_1"
    with pytest.raises(Exception):
        uid.value = "unit_test_2"  # Frozen dataclass

def test_identity_permanence_registry():
    registry = IdentityRegistry()
    uid = UnitID("unit_perm_1")
    
    registry.register_unit(uid)
    assert registry.is_active(uid)
    
    registry.retire_unit(uid)
    assert not registry.is_active(uid)
    assert registry.is_retired(uid)
    
    # Attempting to reuse retired UnitID must raise ValueError
    with pytest.raises(ValueError, match="Identity Violation"):
        registry.register_unit(uid)

def test_graph_version():
    v = GraphVersion(1, 0, 0, 0)
    assert str(v) == "v1.0.0-0"
    v2 = v.next_sequence()
    assert str(v2) == "v1.0.0-1"


@pytest.mark.parametrize(
    "identity_type",
    [UnitID, InstanceID, GraphID, MutationID, TransactionID],
)
@pytest.mark.parametrize("value", [None, "", " whitespace "])
def test_identity_values_must_be_normalized_non_empty_strings(identity_type, value) -> None:
    with pytest.raises(ValueError, match="normalized non-empty string"):
        identity_type(value)


@pytest.mark.parametrize(
    "values",
    [(-1, 0, 0, 0), (1, -1, 0, 0), (1, 0, -1, 0), (1, 0, 0, -1), (True, 0, 0, 0)],
)
def test_graph_version_components_are_non_negative_integers(values) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        GraphVersion(*values)

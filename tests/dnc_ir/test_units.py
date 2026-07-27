from dnc.ir.identity import UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension

def test_computational_unit_dimensions():
    uid = UnitID("unit_calc_1")
    unit = ComputationalUnit(
        unit_id=uid,
        name="Calculator",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    )
    
    assert unit.unit_id == uid
    assert unit.structure == StructureDimension.PRIMITIVE
    assert unit.visibility == VisibilityDimension.INSPECTABLE
    assert unit.lifecycle == LifecycleDimension.BASE
    assert unit.validate_dimensions() is True

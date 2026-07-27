import pytest
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.projection.projector import StructuralProjector
from dnc.runtime.runtime import DNCRuntime
from dnc.state.registry import ModuleRegistry
from dnc.modules.standard import StandardModule

def test_ir_to_execution_core_integration():
    # 1. Create DNC-IR graph
    g = StructuralGraph(graph_id=GraphID("g_integration"))
    u1 = ComputationalUnit(UnitID("mod_1"), "StandardModule", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)

    # 2. Project to Executable DAG
    projector = StructuralProjector()
    dag, warnings = projector.project(g)
    assert dag is not None
    assert len(dag.topological_order) == 1

    # 3. Verify execution via frozen v1.x runtime
    registry = ModuleRegistry()
    registry.register("StandardModule", StandardModule)
    
    runtime = DNCRuntime(registry=registry)
    assert runtime is not None
    assert dag.graph_id.value == "g_integration"

"""Conformance tests for provider integration (architecture.md Section 2.F).

Per architecture.md Section 2.F / Conformance Clause: ExecutionProviders are
bound at dispatch time, not at graph construction time; the scheduler does not
know which provider implements a capability. These tests verify:

  - DEV mode dispatches through the injected module-dispatch function (mock).
  - PROD mode dispatches through a real ExecutionProvider selected by the node's
    capability, and FAILS LOUDLY when no provider is bound for a capability.
  - Provider capability routing selects the correct provider per node.
"""

import sys

sys.path.insert(0, "src")

from dnc.runtime.types import (
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import ExecutionGraph, VertexAssignment
from dnc.runtime.runtime import (
    Runtime,
    ExecutionState2,
    ProviderMode,
)
from dnc.execution.execution_provider import (
    ExecutionCapability,
    ReferenceExecutionProvider,
)


def _build_linear_runtime() -> tuple:
    registry = ModuleRegistry()
    for name in ["SRC", "TR", "SINK"]:
        registry.register(
            ModuleContract(
                module_type_id=ModuleTypeID(name, "h_" + name),
                output_signature=object,
                capabilities=frozenset([name.lower()]),
            )
        )

    runtime = Runtime(config=None, initial_budget=100.0)
    runtime._registry = registry

    es = ExecutionState()
    es.W = WorkingMemory()
    es.M = registry.snapshot()
    es.C = CheckpointRecord()
    es.initialize_from_seed(0)

    mids = {n: ModuleInstanceID(n, 0) for n in ["SRC", "TR", "SINK"]}
    for m in mids.values():
        es.W.register(m)

    graph = ExecutionGraph()
    graph.vertices = [
        VertexAssignment(
            instance_id=mids[n],
            type_id=ModuleTypeID(n, "h_" + n),
            cost_estimate=1.0,
            preference_score=1.0,
        )
        for n in ["SRC", "TR", "SINK"]
    ]
    graph.edges = [
        (mids["SRC"], mids["TR"]),
        (mids["TR"], mids["SINK"]),
    ]
    graph.cost_weights = {m: 1.0 for m in mids.values()}

    sched = Scheduler()
    sched.set_graph(graph.get_vertices(), graph.edges)
    es.G = sched
    runtime._current_graph = graph
    runtime._state = ExecutionState2.RUNNING
    return runtime, es, mids


class TestProviderDispatch:
    """Provider integration at dispatch time (architecture.md Section 2.F)."""

    def test_dev_mode_uses_dispatch_fn(self):
        """DEV (default) routes through the injected dispatch function."""
        runtime, es, mids = _build_linear_runtime()
        seen = {}

        def _dispatch(mid):
            seen[str(mid.type_id)] = seen.get(str(mid.type_id), 0) + 1
            name = mid.type_id
            if name == "SRC":
                return [1.0, 2.0]
            if name == "TR":
                return es.W[mids["SRC"]].output[0] * 2
            return es.W[mids["TR"]].output

        runtime.set_dispatch_fn(_dispatch)
        assert runtime._provider_mode == ProviderMode.DEV

        for _ in range(50):
            runtime.step(es)
            if runtime.state == ExecutionState2.TERMINATED:
                break

        assert runtime.state == ExecutionState2.TERMINATED
        assert seen == {"SRC": 1, "TR": 1, "SINK": 1}
        print("PASS: test_dev_mode_uses_dispatch_fn")

    def test_prod_mode_routes_through_provider(self):
        """PROD dispatches through a provider selected by node capability."""
        runtime, es, mids = _build_linear_runtime()

        provider = ReferenceExecutionProvider(
            provider_id="ref",
            capabilities={ExecutionCapability.CAP_REASONING, ExecutionCapability.CAP_EXECUTION},
        )
        runtime.register_provider(provider)
        runtime.set_provider_mode(ProviderMode.PROD)
        runtime.set_node_capabilities(
            {
                mids["SRC"].type_id: ExecutionCapability.CAP_EXECUTION,
                mids["TR"].type_id: ExecutionCapability.CAP_REASONING,
                mids["SINK"].type_id: ExecutionCapability.CAP_EXECUTION,
            }
        )

        for _ in range(50):
            runtime.step(es)
            if runtime.state == ExecutionState2.TERMINATED:
                break

        assert runtime.state == ExecutionState2.TERMINATED
        # TR is served by the reasoning provider; the provider returns a
        # capability-tagged result for the (list) upstream input.
        tr_out = es.W[mids["TR"]].output
        assert isinstance(tr_out, dict) and tr_out.get("capability") == "CAP_REASONING", (
            f"TR should be served by reasoning provider, got {tr_out!r}"
        )
        print("PASS: test_prod_mode_routes_through_provider")

    def test_prod_mode_fails_loudly_without_provider(self):
        """PROD must fail loudly when no provider serves a node's capability."""
        runtime, es, mids = _build_linear_runtime()

        # Provider only supports REASONING; SRC requires EXECUTION.
        provider = ReferenceExecutionProvider(
            provider_id="ref", capabilities={ExecutionCapability.CAP_REASONING}
        )
        runtime.register_provider(provider)
        runtime.set_provider_mode(ProviderMode.PROD)
        runtime.set_node_capabilities(
            {mids["SRC"].type_id: ExecutionCapability.CAP_EXECUTION}
        )

        raised = False
        try:
            runtime.step(es)
        except RuntimeError as e:
            raised = "no provider bound" in str(e)
        assert raised, "PROD mode must fail loudly when no provider is bound"
        print("PASS: test_prod_mode_fails_loudly_without_provider")


if __name__ == "__main__":
    import traceback

    g = TestProviderDispatch()
    results = []
    for name in sorted(dir(g)):
        if name.startswith("test_"):
            try:
                getattr(g, name)()
                results.append(f"PASS: {name}")
            except Exception as e:  # noqa: BLE001
                results.append(f"FAIL: {name} -- {e}")
                traceback.print_exc()
    for r in results:
        print(r)
    passed = sum(1 for r in results if r.startswith("PASS"))
    print(f"{passed}/{len(results)} conformance tests passed")

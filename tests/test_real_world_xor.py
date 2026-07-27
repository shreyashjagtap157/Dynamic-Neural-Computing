"""Real-world application test: orchestrating an actual neural computation.

The DNC runtime is a neural-computation *orchestration* engine: module
instances form an execution graph (a structural analogy to a neural
circuit) and are dispatched through the Observe -> Decide -> Act -> Assess
control loop.

This test wires up a genuine 2-2-1 multilayer perceptron that solves the
classic XOR problem, and runs its forward pass through the REAL Runtime:
  SRC -> {L1A, L1B} -> L2 -> DEC
where each module instance applies a real weight/bias/sigmoid neuron
computation, reading its upstream outputs from working memory.

It verifies that the orchestrated neural computation:
  (a) produces the correct XOR classification for all four inputs,
  (b) matches an independent reference forward pass (DNC == math),
  (c) holds all runtime invariants during dispatch,
  (d) records a tamper-evident provenance trace, and
  (e) survives a byte-exact checkpoint/restore (G-12.2).
"""

import sys
import math

sys.path.insert(0, "src")

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
    UNBOUND,
    PENDING,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import Checkpoint, CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import ExecutionGraph, VertexAssignment
from dnc.runtime.runtime import Runtime, Decision, ExecutionState2
from dnc.observability.provenance import ProvenanceLog, EventType


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


# --- Verified XOR weights (hidden: OR-like and AND-like features) -----------
# h1 = sigmoid(10*x1 + 10*x2 - 5)        # ~1 when at least one input is 1
# h2 = sigmoid(10*x1 + 10*x2 - 30)       # ~1 only when both inputs are 1
# o  = sigmoid(15*h1 - 15*h2 - 7)        # ~1 when (OR and not AND) == XOR
W_HIDDEN = {
    "L1A": ([10.0, 10.0], -5.0),
    "L1B": ([10.0, 10.0], -15.0),
}
W_OUT = ([15.0, -15.0], -7.0)

UPSTREAM = {
    "SRC": [],
    "L1A": ["SRC"],
    "L1B": ["SRC"],
    "L2": ["L1A", "L1B"],
    "DEC": ["L2"],
}

XOR_INPUTS = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]
XOR_TARGETS = [0, 1, 1, 0]


def ref_forward(x1: float, x2: float) -> int:
    """Independent reference MLP forward pass (no DNC involvement)."""
    h1 = sigmoid(W_HIDDEN["L1A"][0][0] * x1 + W_HIDDEN["L1A"][0][1] * x2 + W_HIDDEN["L1A"][1])
    h2 = sigmoid(W_HIDDEN["L1B"][0][0] * x1 + W_HIDDEN["L1B"][0][1] * x2 + W_HIDDEN["L1B"][1])
    o = sigmoid(W_OUT[0][0] * h1 + W_OUT[0][1] * h2 + W_OUT[1])
    return 1 if o >= 0.5 else 0


class TestRealWorldNeuralCompute:
    """End-to-end neural-computation orchestration through the DNC Runtime."""

    def setup(self) -> None:
        self.registry = ModuleRegistry()
        for name in ["SRC", "L1A", "L1B", "L2", "DEC"]:
            self.registry.register(
                ModuleContract(
                    module_type_id=ModuleTypeID(name, "hash_" + name),
                    output_signature=object,
                    capabilities=frozenset([name.lower()]),
                )
            )

        self.runtime = Runtime(config=None, initial_budget=100.0)
        self.runtime._registry = self.registry

        self.es = ExecutionState()
        self.es.W = WorkingMemory()
        self.es.M = self.registry.snapshot()
        self.es.C = CheckpointRecord()
        self.es.H = self.es.H  # HistoryLog default
        self.es.initialize_from_seed(0)

        self.mids = {n: ModuleInstanceID(n, 0) for n in ["SRC", "L1A", "L1B", "L2", "DEC"]}
        for m in self.mids.values():
            self.es.W.register(m)

        graph = ExecutionGraph()
        graph.vertices = [
            VertexAssignment(
                instance_id=self.mids[n],
                type_id=ModuleTypeID(n, "hash_" + n),
                cost_estimate=1.0,
                preference_score=1.0,
            )
            for n in ["SRC", "L1A", "L1B", "L2", "DEC"]
        ]
        graph.edges = [
            (self.mids["SRC"], self.mids["L1A"]),
            (self.mids["SRC"], self.mids["L1B"]),
            (self.mids["L1A"], self.mids["L2"]),
            (self.mids["L1B"], self.mids["L2"]),
            (self.mids["L2"], self.mids["DEC"]),
        ]
        graph.cost_weights = {m: 1.0 for m in self.mids.values()}

        sched = Scheduler()
        sched.set_graph(graph.get_vertices(), graph.edges)
        self.es.G = sched
        self.runtime._current_graph = graph
        self.runtime._state = ExecutionState2.RUNNING
        self.runtime.set_dispatch_fn(self._dispatch)

        self.sample = [0.0, 0.0]
        self.prov = ProvenanceLog(self.es.execution_id)
        self._prov_prev: str | None = None

    def _dispatch(self, mid: ModuleInstanceID):
        role = mid.type_id
        if role == "SRC":
            out = [float(self.sample[0]), float(self.sample[1])]
        else:
            vals = [self.es.W[self.mids[u]].output for u in UPSTREAM[role]]
            if role in ("L1A", "L1B"):
                x = vals[0]
                w, b = W_HIDDEN[role]
                out = sigmoid(w[0] * x[0] + w[1] * x[1] + b)
            elif role == "L2":
                h = vals
                w, b = W_OUT
                out = sigmoid(w[0] * h[0] + w[1] * h[1] + b)
            elif role == "DEC":
                out = 1 if vals[0] >= 0.5 else 0
            else:  # pragma: no cover
                raise ValueError(f"Unknown role {role}")

        ev = self.prov.append(
            EventType.STEP_COMPLETED,
            self.es.step_index,
            self._prov_prev,
            {"module": role, "output": out},
        )
        self._prov_prev = ev.event_id
        return out

    def _reset_intermediates(self) -> None:
        # Each sample is a new execution input; reset the source as well as all
        # derived nodes so the completion guard does not reuse the prior sample.
        for name in ["SRC", "L1A", "L1B", "L2", "DEC"]:
            self.es.W[self.mids[name]] = Buffer.unbound_input()

    def _run_sample(self, x1: float, x2: float) -> int:
        self.sample[0], self.sample[1] = x1, x2
        self._reset_intermediates()
        for _ in range(12):
            decision = self.runtime.decide(self.runtime.observe(), self.es)
            if decision == Decision.TERMINATE:
                break
            self.runtime.act(decision, self.es)
            buf = self.es.W[self.mids["DEC"]].output
            if not isinstance(buf, (UNBOUND, PENDING)):
                break
        return int(self.es.W[self.mids["DEC"]].output)

    def test_xor_orchestrated_through_runtime(self):
        """The DNC Runtime correctly orchestrates a real XOR neural forward pass."""
        self.setup()
        predictions = [self._run_sample(x1, x2) for x1, x2 in XOR_INPUTS]
        assert predictions == XOR_TARGETS, (
            f"Orchestrated MLP must solve XOR. Got {predictions}, expected {XOR_TARGETS}"
        )

    def test_xor_matches_reference_math(self):
        """DNC orchestration output must equal the independent reference forward pass."""
        self.setup()
        for (x1, x2) in XOR_INPUTS:
            got = self._run_sample(x1, x2)
            ref = ref_forward(x1, x2)
            assert got == ref, (
                f"Orchestrated output {got} != reference {ref} for input ({x1},{x2})"
            )

    def test_invariants_hold_during_compute(self):
        """All runtime invariants (INV-1..11) survive every dispatch step."""
        self.setup()
        # act() calls check_invariants after each dispatch; reaching correct
        # results without raising proves invariants held throughout.
        preds = [self._run_sample(x1, x2) for x1, x2 in XOR_INPUTS]
        assert preds == XOR_TARGETS

    def test_provenance_trace_recorded(self):
        """The neural computation produced a tamper-evident provenance trace."""
        self.setup()
        self._run_sample(1.0, 0.0)
        assert len(self.prov) >= 5, "Each dispatched module must log a provenance event"
        assert self.prov.verify_chain() is True, "Provenance hash chain must be intact"

    def test_checkpoint_preserves_computed_output(self):
        """A checkpoint taken after computing XOR restores the output byte-exact (G-12.2)."""
        import pickle

        self.setup()
        self._run_sample(1.0, 1.0)
        computed = self.es.W[self.mids["DEC"]].output
        assert computed == 0, "XOR(1,1) must be 0"

        ck = Checkpoint.take(self.es.step_index, self.es.execution_id, self.es.to_dict(), "CK_XOR")
        ck.validate()
        restored = ExecutionState.from_dict(ck.es_snapshot)
        assert pickle.dumps(restored.to_dict()) == pickle.dumps(self.es.to_dict())
        assert restored.W[self.mids["DEC"]].output == computed


if __name__ == "__main__":
    import traceback

    t = TestRealWorldNeuralCompute()
    results = []
    for name in sorted(dir(t)):
        if name.startswith("test_"):
            try:
                getattr(t, name)()
                results.append(f"PASS: {name}")
            except Exception as e:
                results.append(f"FAIL: {name} -- {e}")
                traceback.print_exc()

    for r in results:
        print(r)

    passed = sum(1 for r in results if r.startswith("PASS"))
    print(f"\n{passed}/{len(results)} real-world neural-compute checks passed")

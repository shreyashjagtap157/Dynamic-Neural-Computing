"""Executable evidence for INV-POL-1 through INV-POL-5."""

from dnc.execution.decision_policy import Decision as PolicyDecision, RulePolicy
from dnc.runtime.runtime import Runtime
from dnc.runtime.types import ModuleContract, ModuleTypeID


class ReplanPolicy(RulePolicy):
    def decide(self, observation, execution_state):
        super().decide(observation, execution_state)
        return PolicyDecision.REPLAN


def _runtime(policy=None):
    runtime = Runtime(decision_policy=policy or RulePolicy())
    runtime.register_module(
        ModuleContract(module_type_id=ModuleTypeID("Source", "v1"), output_signature=object)
    )
    state = runtime.initiate("policy")
    runtime.set_dispatch_fn(lambda mid: 1)
    return runtime, state


def test_inv_pol_1_policy_invoked_in_decide() -> None:
    """INV-POL-1: DecisionPolicy.decide is invoked at every Decide phase."""
    runtime, state = _runtime()
    before = runtime.decision_policy.get_decision_metadata().reasoning
    runtime.step(state)
    after = runtime.decision_policy.get_decision_metadata().reasoning
    assert before == "No decision made yet"
    assert after != before


def test_inv_pol_2_policy_returns_closed_decision_enum() -> None:
    """INV-POL-2: policy returns exactly CONTINUE/REPLAN/PAUSE/TERMINATE/ROLLBACK."""
    assert {item.name for item in PolicyDecision} == {
        "CONTINUE", "REPLAN", "PAUSE", "TERMINATE", "ROLLBACK"
    }


def test_inv_pol_3_can_replan_respects_critical_section_and_limit() -> None:
    """INV-POL-3: can_replan is false in critical sections and at the limit."""
    policy = RulePolicy(max_replans=1, replan_coolout_steps=0)
    policy.set_critical_section(True)
    assert not policy.can_replan()
    policy.set_critical_section(False)
    runtime, state = _runtime(policy)
    policy.decide({"failure_detected": True}, state)
    assert not policy.can_replan()


def test_inv_pol_4_replan_decision_invokes_planner_and_replaces_graph() -> None:
    """INV-POL-4: REPLAN invokes Planner and produces an ExecutionGraph."""
    runtime, state = _runtime(ReplanPolicy())
    before = runtime._current_graph
    runtime.step(state)
    assert runtime.replan_count == 1
    assert runtime._current_graph is not None
    assert runtime._current_graph is not before


def test_inv_pol_5_trace_records_policy_version() -> None:
    """INV-POL-5: every decision trace stores the DecisionPolicy version."""
    policy = RulePolicy()
    runtime, state = _runtime(policy)
    runtime.step(state)
    assert runtime.execution_trace.execution_record[0].decision.policy_version == policy.version

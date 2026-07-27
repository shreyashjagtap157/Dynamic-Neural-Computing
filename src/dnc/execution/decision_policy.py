"""DecisionPolicy: abstraction for selecting the next action in the control loop.

Per decision-policy.md: DecisionPolicy is NOT the Planner. DecisionPolicy decides
what to do (CONTINUE/REPLAN/PAUSE/TERMINATE/ROLLBACK); the Planner does it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

import time

from dnc.state.execution_state import ExecutionState


class Decision(Enum):
    """Actions available to the DecisionPolicy (per decision-policy.md Section 2.B)."""

    CONTINUE = auto()
    REPLAN = auto()
    PAUSE = auto()
    TERMINATE = auto()
    ROLLBACK = auto()


@dataclass(frozen=True)
class DecisionMetadata:
    """Per decision-policy.md Section 2.C: metadata recorded for each decision."""

    decision: Decision
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    alternative_considered: List[Decision] = field(default_factory=list)
    policy_version: str = ""
    latency_ms: float = 0.0


class DecisionPolicy(ABC):
    """Abstract decision policy interface (per decision-policy.md Section 2.A)."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Version string for this policy implementation."""

    @property
    @abstractmethod
    def policy_type(self) -> str:
        """Policy type identifier (rule / llm / rl / human)."""

    @abstractmethod
    def decide(
        self,
        observation: Any,
        execution_state: ExecutionState,
    ) -> Decision:
        """Select the next action based on observation and state.

        Args:
            observation: Signals received since last iteration
            execution_state: Current ES(t) = (W, M, C, H, R)

        Returns:
            Decision: CONTINUE / REPLAN / PAUSE / TERMINATE / ROLLBACK
        """

    @abstractmethod
    def can_replan(self) -> bool:
        """Return True if replanning is currently allowed.

        May return False during critical sections or when replan limit is reached.
        """

    @abstractmethod
    def get_decision_metadata(self) -> DecisionMetadata:
        """Return metadata about the last decision for trace recording."""


class RulePolicy(DecisionPolicy):
    """Reference rule-based decision policy (per decision-policy.md Section 3.A).

    Rules are evaluated in priority order:
    1. If critical_section: CONTINUE
    2. If replan_limit_reached: TERMINATE
    3. If resource_exhausted: REPLAN (if can_replan)
    4. If step_deadline_missed: REPLAN (if can_replan)
    5. If failure_detected: REPLAN or ROLLBACK or TERMINATE
    6. If all_modules_complete: TERMINATE
    7. Otherwise: CONTINUE
    """

    def __init__(
        self,
        max_replans: int = 10,
        resource_threshold: float = 0.1,
        replan_coolout_steps: int = 3,
    ) -> None:
        self._version = "1.0.0"
        self._policy_type = "rule"
        self._max_replans = max_replans
        self._resource_threshold = resource_threshold
        self._replan_cooldown_steps = replan_coolout_steps
        self._replan_count = 0
        self._last_replan_step = -1
        self._last_decision: Optional[Decision] = None
        self._last_metadata: Optional[DecisionMetadata] = None
        self._critical_section = False

    @property
    def version(self) -> str:
        return self._version

    @property
    def policy_type(self) -> str:
        return self._policy_type

    def set_critical_section(self, active: bool) -> None:
        """Enable/disable critical section mode (blocks REPLAN decisions)."""
        self._critical_section = active

    def set_observation(self, observation: Any) -> None:
        """Store the latest observation for decision evaluation."""
        self._current_observation = observation

    def set_execution_state(self, es: ExecutionState) -> None:
        """Store the latest execution state for decision evaluation."""
        self._current_es = es

    def decide(
        self,
        observation: Any,
        execution_state: ExecutionState,
    ) -> Decision:
        t_start = time.time()
        self._current_observation = observation
        self._current_es = execution_state

        decision = self._apply_rules()

        latency = (time.time() - t_start) * 1000
        alternatives = [d for d in Decision if d != decision]

        self._last_decision = decision
        self._last_metadata = DecisionMetadata(
            decision=decision,
            reasoning=self._get_reasoning(decision),
            confidence=1.0,
            alternative_considered=alternatives,
            policy_version=self._version,
            latency_ms=latency,
        )

        if decision == Decision.REPLAN:
            self._replan_count += 1
            self._last_replan_step = execution_state.step_index

        return decision

    def _apply_rules(self) -> Decision:
        es = self._current_es
        obs = self._current_observation

        if self._critical_section:
            return Decision.CONTINUE

        if self._replan_count >= self._max_replans:
            return Decision.TERMINATE

        if self._is_resource_exhausted(es):
            if self.can_replan():
                return Decision.REPLAN

        if self._is_failure_detected(obs, es):
            if self.can_replan():
                return Decision.REPLAN
            return Decision.ROLLBACK

        if self._is_all_modules_complete(es):
            return Decision.TERMINATE

        if self._is_step_deadline_missed(es):
            if self.can_replan():
                return Decision.REPLAN

        return Decision.CONTINUE

    def _is_resource_exhausted(self, es: ExecutionState) -> bool:
        remaining = es.budget_remaining
        if remaining is None:
            return False
        return remaining < self._resource_threshold

    def _is_failure_detected(self, observation: Any, es: ExecutionState) -> bool:
        if observation is None:
            return False
        if isinstance(observation, dict):
            return observation.get("failure_detected", False)
        return False

    def _is_all_modules_complete(self, es: ExecutionState) -> bool:
        pending = es.pending_count
        return pending == 0

    def _is_step_deadline_missed(self, es: ExecutionState) -> bool:
        return False

    def _get_reasoning(self, decision: Decision) -> str:
        if self._critical_section:
            return "Critical section active — continuing"
        if self._replan_count >= self._max_replans:
            return f"Replan limit reached ({self._max_replans})"
        if self._is_resource_exhausted(self._current_es):
            return "Resource budget exhausted"
        if self._is_failure_detected(self._current_observation, self._current_es):
            return "Failure detected"
        if self._is_all_modules_complete(self._current_es):
            return "All modules complete"
        if self._is_step_deadline_missed(self._current_es):
            return "Step deadline missed"
        return "Default: continue"

    def can_replan(self) -> bool:
        if self._critical_section:
            return False
        if self._replan_count >= self._max_replans:
            return False
        es = getattr(self, "_current_es", None)
        if es is None:
            return True
        if es.step_index - self._last_replan_step < self._replan_cooldown_steps:
            return False
        return True

    def get_decision_metadata(self) -> DecisionMetadata:
        if self._last_metadata is None:
            return DecisionMetadata(
                decision=Decision.CONTINUE,
                reasoning="No decision made yet",
                policy_version=self._version,
            )
        return self._last_metadata

    def reset(self) -> None:
        self._replan_count = 0
        self._last_replan_step = -1
        self._last_decision = None
        self._last_metadata = None
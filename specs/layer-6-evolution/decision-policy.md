# Decision Policy

## Metadata

| Field | Value |
|---|---|
| Document | decision-policy.md |
| Title | Decision Policy |
| Document ID | SPEC-DEC-POL |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | How does the runtime decide what to do next? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md |
| Defines | DecisionPolicy interface, DecisionAction, RulePolicy, LLMPolicy, RLPolicy |
| Referenced by | conformance-model.md |

---

## Section 1 — Overview

### 1.A Purpose

The **DecisionPolicy** is the component of the DNC runtime that selects the next action (CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK) at each control loop iteration.

The DecisionPolicy is invoked by the control loop during the Decide phase. It receives the current observation and execution state and returns a decision.

### 1.B Design Principle

**The DecisionPolicy is not the Planner.** This is the most important design principle.

- The DecisionPolicy **decides what to do** (CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK)
- The Planner **does it** (synthesizes the new execution graph when asked)

The planner is a service invoked by the control loop when the DecisionPolicy selects REPLAN. The DecisionPolicy does not plan; it decides whether to ask the planner to plan.

### 1.C Action Space

The DecisionPolicy selects from five actions:

| Action | Meaning |
|---|---|
| **CONTINUE** | Proceed with the current execution graph without modification |
| **REPLAN** | Invoke the planner to synthesize a new execution graph |
| **PAUSE** | Suspend execution and await resumption signals without terminating or replanning |
| **TERMINATE** | End the control loop; execution is complete |
| **ROLLBACK** | Revert execution state to a prior checkpoint and resume from there |

---

## Section 2 — DecisionPolicy Interface

### 2.A Abstract Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

class DecisionPolicy(ABC):
    """Abstract decision policy interface."""

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
        observation: Observation,
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
    def get_decision_metadata(self) -> Dict[str, Any]:
        """Return metadata about the last decision for trace recording."""
```

### 2.B Decision Enum

```python
from enum import Enum, auto

class Decision(Enum):
    """Actions available to the DecisionPolicy."""

    CONTINUE = auto()    # Proceed with current graph
    REPLAN = auto()      # Synthesize new graph
    PAUSE = auto()       # Suspend execution
    TERMINATE = auto()   # End execution
    ROLLBACK = auto()    # Revert to checkpoint
```

### 2.C DecisionMetadata

```python
@dataclass(frozen=True)
class DecisionMetadata:
    """Metadata recorded for each decision in the trace."""

    decision: Decision
    reasoning: Optional[str]        # Explanation of the decision (especially for LLMPolicy)
    confidence: Optional[float]     # Confidence score (0.0-1.0), if available
    alternative_considered: List[Decision]  # Other options considered
    policy_version: str             # Version of the policy that made the decision
    latency_ms: float                # Time to produce the decision
```

---

## Section 3 — Policy Implementations

### 3.A RulePolicy (Reference Implementation)

The **RulePolicy** is the reference implementation. It applies fixed pre-defined rules to select actions.

```python
class RulePolicy(DecisionPolicy):
    """Reference rule-based decision policy.

    Rules are evaluated in priority order:
    1. If critical_section: CONTINUE
    2. If replan_limit_reached: TERMINATE
    3. If resource_exhausted: REPLAN (if can_replan)
    4. If step_deadline_missed: REPLAN (if can_replan)
    5. If failure_detected: REPLAN (if can_replan) or ROLLBACK or TERMINATE
    6. If all_modules_complete: TERMINATE
    7. If pause_signal: PAUSE
    8. Otherwise: CONTINUE
    """

    def __init__(
        self,
        resource_threshold: float = 0.1,
        max_replans: int = 3,
        enable_rollback: bool = True,
        rollback_on_failure: bool = True,
    ) -> None:
        self._resource_threshold = resource_threshold
        self._max_replans = max_replans
        self._enable_rollback = enable_rollback
        self._rollback_on_failure = rollback_on_failure
        self._replan_count = 0

    def decide(self, observation: Observation, execution_state: ExecutionState) -> Decision:
        # Implementation of rule-based decision logic
        pass

    def can_replan(self) -> bool:
        return self._replan_count < self._max_replans

    def reset_replan_count(self) -> None:
        self._replan_count = 0
```

### 3.B LLMPolicy

The **LLMPolicy** uses a language model to select the next action based on the execution context.

```python
class LLMPolicy(DecisionPolicy):
    """Decision policy driven by a language model.

    The LLM receives a structured prompt describing:
    - Current execution state
    - Recent observations
    - Available actions and their implications
    - Policy constraints

    The LLM returns a structured decision with reasoning.
    """

    def __init__(
        self,
        llm_provider: "LLMProvider",
        model: Optional[str] = None,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
        max_replans: int = 3,
    ) -> None:
        self._llm = llm_provider
        self._model = model
        self._temperature = temperature
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._max_replans = max_replans
        self._replan_count = 0

    def decide(self, observation: Observation, execution_state: ExecutionState) -> Decision:
        prompt = self._build_prompt(observation, execution_state)
        response = self._llm.chat(
            messages=[
                ChatMessage(role="system", content=self._system_prompt),
                ChatMessage(role="user", content=prompt),
            ],
            model=self._model,
            temperature=self._temperature,
        )
        return self._parse_decision(response)

    def _build_prompt(self, observation: Observation, es: ExecutionState) -> str:
        # Builds a structured description of current state
        pass

    def _parse_decision(self, response: LLMResponse) -> Decision:
        # Parses the LLM response into a Decision
        pass

    def can_replan(self) -> bool:
        return self._replan_count < self._max_replans

    @property
    def policy_type(self) -> str:
        return "llm"
```

### 3.C RLPolicy (Future)

The **RLPolicy** is a decision policy trained via reinforcement learning on execution traces.

```python
class RLPolicy(DecisionPolicy):
    """Decision policy trained via reinforcement learning.

    The policy is trained to optimize a reward function that balances:
    - Task completion (final outcome quality)
    - Resource efficiency (tokens spent, time used)
    - Adaptation quality (DCI, CCG)
    - Recovery effectiveness (rollback success rate)

    Training uses execution traces as training data.
    """

    def __init__(
        self,
        model_path: str,
        reward_function: "RewardFunction",
        max_replans: int = 3,
    ) -> None:
        self._model = self._load_model(model_path)
        self._reward_fn = reward_function
        self._max_replans = max_replans
        self._replan_count = 0

    def decide(self, observation: Observation, execution_state: ExecutionState) -> Decision:
        state_vector = self._encode_state(observation, execution_state)
        action_logits = self._model.predict(state_vector)
        return self._logits_to_decision(action_logits)

    def can_replan(self) -> bool:
        return self._replan_count < self._max_replans

    @property
    def policy_type(self) -> str:
        return "rl"
```

---

## Section 4 — Decision Policy Invariants

**INV-POL-1:** DecisionPolicy.decide() MUST be invoked at every control loop iteration during the Decide phase.

**INV-POL-2:** DecisionPolicy.decide() MUST return exactly one of: CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK.

**INV-POL-3:** DecisionPolicy.can_replan() MUST return False during critical sections or when the replan limit is reached.

**INV-POL-4:** When DecisionPolicy returns REPLAN, the control loop MUST invoke the Planner and the Planner MUST produce a new ExecutionGraph.

**INV-POL-5:** The DecisionPolicy's version MUST be recorded in the trace for every decision.

---

## Section 5 — Conformance Clause

An implementation conforms to this specification if:

- All DecisionPolicy implementations implement the interface in Section 2
- All five Decision values are supported
- INV-POL-1 through INV-POL-5 are enforced
- The RulePolicy implements the reference rule set correctly
- Policy swapping (RulePolicy ↔ LLMPolicy ↔ RLPolicy) does not require control loop changes

Extensions are permitted only under `conformance-model.md` Section 3. Policy-specific extensions use the POL-* namespace.

---

## Section 6 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| POL-AMEND-001 | decision-policy.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of DecisionPolicy interface, Decision enum, RulePolicy, LLMPolicy, RLPolicy, INV-POL-1 through INV-POL-5. | No |
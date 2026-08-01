"""Decision-log validation for support, overlap, completeness, and leakage."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.cognition.canonical import canonical_hash
from dnc.policy_learning.contracts import DecisionExample


@dataclass(frozen=True)
class DatasetValidation:
    valid: bool
    errors: tuple[str, ...]
    data_hash: str
    minimum_propensity: float
    supported_fraction: float


def validate_decision_dataset(examples: tuple[DecisionExample, ...]) -> DatasetValidation:
    errors: list[str] = []
    seen: set[str] = set()
    train_tasks: set[str] = set()
    evaluation_tasks: set[str] = set()
    supported = 0
    propensities: list[float] = []
    for example in examples:
        if example.decision_id in seen:
            errors.append(f"DUPLICATE_DECISION:{example.decision_id}")
        seen.add(example.decision_id)
        if not example.candidates:
            errors.append(f"EMPTY_CANDIDATES:{example.decision_id}")
            continue
        ids = [item.action_id for item in example.candidates]
        if len(ids) != len(set(ids)):
            errors.append(f"DUPLICATE_CANDIDATE:{example.decision_id}")
        if example.selected_action_id not in ids:
            errors.append(f"SELECTED_ACTION_MISSING:{example.decision_id}")
        probability_sum = sum(item.propensity for item in example.candidates)
        if abs(probability_sum - 1.0) > 1e-6:
            errors.append(f"PROPENSITY_SUM:{example.decision_id}")
        propensities.extend(item.propensity for item in example.candidates)
        if all(item.propensity > 0 for item in example.candidates):
            supported += 1
        if example.outcome is None and not example.censored:
            errors.append(f"MISSING_OUTCOME:{example.decision_id}")
        (train_tasks if example.split == "train" else evaluation_tasks).add(
            example.task_fingerprint
        )
    leakage = train_tasks & evaluation_tasks
    if leakage:
        errors.append("TASK_SPLIT_LEAKAGE:" + ",".join(sorted(leakage)))
    return DatasetValidation(
        not errors,
        tuple(errors),
        canonical_hash(examples, namespace="dnc.decision-dataset.v1"),
        min(propensities, default=0.0),
        supported / len(examples) if examples else 0.0,
    )

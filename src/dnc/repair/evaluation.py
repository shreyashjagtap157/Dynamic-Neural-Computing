"""Localized repair correctness and preservation metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairEvaluation:
    correctness_matches_full: bool
    repair_precision: float
    unaffected_preservation: float
    avoided_recomputation_fraction: float


def evaluate_repair(
    *,
    localized_values: dict[str, object],
    full_recompute_values: dict[str, object],
    affected_ids: tuple[str, ...],
    original_values: dict[str, object],
) -> RepairEvaluation:
    all_ids = set(full_recompute_values)
    affected = set(affected_ids)
    unaffected = all_ids - affected
    correctness = localized_values == full_recompute_values
    changed = {key for key in all_ids if localized_values.get(key) != original_values.get(key)}
    precision = len(changed & affected) / len(changed) if changed else 1.0
    preservation = (
        sum(localized_values.get(key) == original_values.get(key) for key in unaffected) / len(unaffected)
        if unaffected else 1.0
    )
    return RepairEvaluation(
        correctness,
        precision,
        preservation,
        len(unaffected) / len(all_ids) if all_ids else 0.0,
    )

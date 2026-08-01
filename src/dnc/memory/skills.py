"""Skill induction, lifecycle, promotion, rollback, and drift invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dnc.memory.contracts import Episode, SkillEvaluation, SkillLifecycle, SkillManifest


_FORWARD = {
    SkillLifecycle.DRAFT: SkillLifecycle.SANDBOXED,
    SkillLifecycle.SANDBOXED: SkillLifecycle.EVALUATED,
    SkillLifecycle.EVALUATED: SkillLifecycle.SHADOW,
    SkillLifecycle.SHADOW: SkillLifecycle.CANARY,
    SkillLifecycle.CANARY: SkillLifecycle.ACTIVE,
}


def induce_skill(
    *,
    skill_id: str,
    version: str,
    name: str,
    procedure: tuple[str, ...],
    permissions: frozenset[str],
    domains: frozenset[str],
    episodes: tuple[Episode, ...],
    dependency_fingerprints: frozenset[str] = frozenset(),
) -> SkillManifest:
    positive = tuple(item for item in episodes if item.verified and not item.negative and item.outcome > 0)
    negative = tuple(item for item in episodes if item.verified and item.negative)
    if not positive:
        raise ValueError("skill induction requires a verified positive episode")
    tenant_ids = {item.tenant_id for item in episodes}
    if len(tenant_ids) != 1:
        raise ValueError("skill induction cannot cross tenant boundaries")
    return SkillManifest(
        skill_id, version, positive[0].tenant_id, name, procedure, permissions, domains,
        tuple(item.episode_id for item in positive),
        tuple(item.episode_id for item in negative),
        dependency_fingerprints=dependency_fingerprints,
    )


@dataclass
class SkillRegistry:
    _versions: dict[tuple[str, str], SkillManifest] = field(default_factory=dict)
    _evaluations: dict[str, SkillEvaluation] = field(default_factory=dict)
    _disabled: set[str] = field(default_factory=set)

    def register(self, manifest: SkillManifest) -> None:
        key = (manifest.skill_id, manifest.version)
        if key in self._versions:
            raise ValueError(f"skill version already exists: {key}")
        self._versions[key] = manifest

    def get(self, skill_id: str, version: str) -> SkillManifest | None:
        return self._versions.get((skill_id, version))

    def transition(self, skill_id: str, version: str, lifecycle: SkillLifecycle) -> SkillManifest:
        current = self._require(skill_id, version)
        if lifecycle is current.lifecycle:
            return current
        if lifecycle not in {SkillLifecycle.QUARANTINED, SkillLifecycle.RETIRED, SkillLifecycle.ROLLED_BACK}:
            if _FORWARD.get(current.lifecycle) is not lifecycle:
                raise ValueError(f"illegal skill lifecycle transition: {current.lifecycle} -> {lifecycle}")
        if lifecycle is SkillLifecycle.EVALUATED:
            evaluation = self._evaluations.get(current.fingerprint)
            if evaluation is None:
                raise ValueError("skill evaluation artifact is required")
            current = replace(current, evaluation_artifact_ids=(evaluation.artifact_id,))
        if lifecycle in {SkillLifecycle.SHADOW, SkillLifecycle.CANARY, SkillLifecycle.ACTIVE}:
            evaluation = self._evaluations.get(current.fingerprint)
            if evaluation is None or not evaluation.promotable:
                raise ValueError("skill does not meet promotion thresholds")
        if lifecycle is SkillLifecycle.ACTIVE:
            for key, other in tuple(self._versions.items()):
                if (
                    other.skill_id == current.skill_id
                    and other.tenant_id == current.tenant_id
                    and other.version != current.version
                    and other.lifecycle is SkillLifecycle.ACTIVE
                ):
                    self._versions[key] = replace(other, lifecycle=SkillLifecycle.ROLLED_BACK)
        updated = replace(current, lifecycle=lifecycle)
        self._versions[(skill_id, version)] = updated
        return updated

    def record_evaluation(self, evaluation: SkillEvaluation) -> None:
        if evaluation.skill_fingerprint not in {item.fingerprint for item in self._versions.values()}:
            raise KeyError("evaluation references unknown skill fingerprint")
        self._evaluations[evaluation.skill_fingerprint] = evaluation

    def active(self, *, tenant_id: str, domain: str, permissions: frozenset[str]) -> tuple[SkillManifest, ...]:
        return tuple(
            item for item in sorted(self._versions.values(), key=lambda value: (value.skill_id, value.version))
            if item.lifecycle is SkillLifecycle.ACTIVE
            and item.skill_id not in self._disabled
            and item.tenant_id == tenant_id
            and domain in item.domains
            and item.permissions <= permissions
        )

    def invalidate(self, changed_fingerprints: set[str]) -> tuple[str, ...]:
        changed = []
        for key, item in tuple(self._versions.items()):
            if item.dependency_fingerprints & changed_fingerprints and item.lifecycle not in {
                SkillLifecycle.RETIRED, SkillLifecycle.ROLLED_BACK,
            }:
                self._versions[key] = replace(item, lifecycle=SkillLifecycle.QUARANTINED)
                changed.append(f"{item.skill_id}:{item.version}")
        return tuple(sorted(changed))

    def rollback(self, skill_id: str, version: str) -> SkillManifest:
        failed = self.transition(skill_id, version, SkillLifecycle.ROLLED_BACK)
        if failed.parent_version is not None:
            parent = self._require(skill_id, failed.parent_version)
            evaluation = self._evaluations.get(parent.fingerprint)
            if evaluation is None or not evaluation.promotable:
                raise ValueError("parent skill version is not qualified for rollback")
            self._versions[(skill_id, parent.version)] = replace(
                parent, lifecycle=SkillLifecycle.ACTIVE
            )
        return failed

    def disable(self, skill_id: str) -> None:
        if not any(key[0] == skill_id for key in self._versions):
            raise KeyError(f"unknown skill: {skill_id}")
        self._disabled.add(skill_id)

    def snapshot(self):
        return (dict(self._versions), dict(self._evaluations), set(self._disabled))

    def restore(self, state) -> None:
        versions, evaluations, disabled = state
        self._versions = dict(versions)
        self._evaluations = dict(evaluations)
        self._disabled = set(disabled)

    def _require(self, skill_id: str, version: str) -> SkillManifest:
        item = self.get(skill_id, version)
        if item is None:
            raise KeyError(f"unknown skill version: {skill_id}:{version}")
        return item

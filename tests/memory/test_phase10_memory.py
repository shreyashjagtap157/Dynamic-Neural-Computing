from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnc.memory import (
    Episode,
    GovernedMemory,
    MemoryKind,
    MemoryRecord,
    SkillEvaluation,
    SkillLifecycle,
    SkillRegistry,
    TransferEvaluation,
    compress_records,
    induce_skill,
)
from dnc.system import DNCSystem


def _record(record_id="r1", kind=MemoryKind.EPISODIC, **changes):
    values = dict(
        record_id=record_id,
        kind=kind,
        tenant_id="tenant-a",
        content="verified payment outcome",
        provenance=("event-1",),
        security_labels=frozenset({"internal"}),
        trust=0.9,
        created_at_ns=10,
        expires_at_ns=100,
        domain="payments",
        integrity_verified=True,
    )
    values.update(changes)
    return MemoryRecord(**values)


def _episodes():
    return (
        Episode("positive", "tenant-a", "task-a", ("retrieve", "verify"), 1.0, True, ("e1",)),
        Episode("negative", "tenant-a", "task-b", ("guess",), -1.0, True, ("e2",), True),
    )


def _skill():
    return induce_skill(
        skill_id="verify-payment", version="1.0.0", name="Verify payment",
        procedure=("retrieve", "verify"), permissions=frozenset({"payments:read"}),
        domains=frozenset({"payments"}), episodes=_episodes(),
        dependency_fingerprints=frozenset({"model-v1", "policy-v1"}),
    )


def test_six_memory_namespaces_are_separate_and_kind_checked() -> None:
    memory = GovernedMemory()
    for index, kind in enumerate(MemoryKind):
        memory.put(_record(f"r{index}", kind))
        assert len(memory.store(kind).snapshot()) == 1
    with pytest.raises(ValueError, match="kind"):
        memory.store(MemoryKind.WORKING).put(_record("wrong", MemoryKind.AUDIT))


def test_retrieval_enforces_tenant_acl_freshness_trust_domain_and_exact_critical_rerank() -> None:
    memory = GovernedMemory()
    memory.put(_record())
    memory.put(_record("expired", expires_at_ns=20))
    memory.put(_record("untrusted", trust=0.1))
    memory.put(_record("secret", security_labels=frozenset({"secret"})))
    memory.put(_record("other", tenant_id="tenant-b"))
    memory.put(_record("poisoned", integrity_verified=False, trust=1.0))
    with pytest.raises(ValueError, match="exact reranker"):
        memory.store(MemoryKind.EPISODIC).retrieve(
            tenant_id="tenant-a", allowed_labels=frozenset({"internal"}), now_ns=50, critical=True
        )
    found = memory.store(MemoryKind.EPISODIC).retrieve(
        tenant_id="tenant-a", allowed_labels=frozenset({"internal"}), now_ns=50,
        minimum_trust=0.8, domain="payments", critical=True,
        exact_reranker=lambda record: 1.0 if record.record_id == "r1" else 0.0,
    )
    assert [item.record_id for item in found] == ["r1"]


def test_critical_retrieval_blocks_unverified_poisoning_even_with_high_trust() -> None:
    memory = GovernedMemory()
    memory.put(_record("poisoned", integrity_verified=False, trust=1.0))
    found = memory.store(MemoryKind.EPISODIC).retrieve(
        tenant_id="tenant-a", allowed_labels=frozenset({"internal"}), now_ns=50,
        critical=True, exact_reranker=lambda _: 1.0,
    )
    assert found == ()


def test_deletion_honors_legal_hold_and_retains_tombstone() -> None:
    memory = GovernedMemory()
    memory.put(_record("held", legal_hold=True))
    with pytest.raises(PermissionError, match="legal hold"):
        memory.store(MemoryKind.EPISODIC).delete("held", tenant_id="tenant-a")
    memory.put(_record("delete"))
    memory.store(MemoryKind.EPISODIC).delete("delete", tenant_id="tenant-a")
    tombstone = next(item for item in memory.store(MemoryKind.EPISODIC).snapshot() if item.record_id == "delete")
    assert tombstone.deleted and tombstone.content is None


def test_skill_induction_requires_verified_positive_and_is_tenant_isolated() -> None:
    skill = _skill()
    assert skill.source_episode_ids == ("positive",)
    assert skill.negative_episode_ids == ("negative",)
    with pytest.raises(ValueError, match="verified positive"):
        induce_skill(
            skill_id="bad", version="1", name="bad", procedure=("guess",),
            permissions=frozenset(), domains=frozenset({"x"}), episodes=(_episodes()[1],),
        )
    with pytest.raises(ValueError, match="tenant"):
        induce_skill(
            skill_id="cross", version="1", name="cross", procedure=("x",),
            permissions=frozenset(), domains=frozenset({"x"}),
            episodes=(_episodes()[0], replace(_episodes()[1], tenant_id="tenant-b")),
        )


def test_skill_promotion_requires_evidence_and_scopes_active_reuse() -> None:
    registry = SkillRegistry()
    skill = _skill()
    registry.register(skill)
    registry.transition(skill.skill_id, skill.version, SkillLifecycle.SANDBOXED)
    with pytest.raises(ValueError, match="evaluation"):
        registry.transition(skill.skill_id, skill.version, SkillLifecycle.EVALUATED)
    evaluation = SkillEvaluation("eval-1", skill.fingerprint, 20, 0.6, 0.8, 0.02, 1.0)
    registry.record_evaluation(evaluation)
    for state in (
        SkillLifecycle.EVALUATED, SkillLifecycle.SHADOW,
        SkillLifecycle.CANARY, SkillLifecycle.ACTIVE,
    ):
        registry.transition(skill.skill_id, skill.version, state)
    assert registry.active(
        tenant_id="tenant-a", domain="payments", permissions=frozenset({"payments:read"})
    ) == (registry.get(skill.skill_id, skill.version),)
    assert registry.active(
        tenant_id="tenant-a", domain="payments", permissions=frozenset()
    ) == ()


def test_harmful_skill_cannot_promote_and_drift_quarantines_active_skill() -> None:
    registry = SkillRegistry()
    skill = _skill()
    registry.register(skill)
    registry.transition(skill.skill_id, skill.version, SkillLifecycle.SANDBOXED)
    registry.record_evaluation(SkillEvaluation("bad", skill.fingerprint, 10, 0.6, 0.9, 0.2, 1.0))
    registry.transition(skill.skill_id, skill.version, SkillLifecycle.EVALUATED)
    with pytest.raises(ValueError, match="threshold"):
        registry.transition(skill.skill_id, skill.version, SkillLifecycle.SHADOW)

    good = SkillRegistry()
    good.register(skill)
    good.transition(skill.skill_id, skill.version, SkillLifecycle.SANDBOXED)
    good.record_evaluation(SkillEvaluation("good", skill.fingerprint, 10, 0.6, 0.9, 0.0, 1.0))
    for state in (SkillLifecycle.EVALUATED, SkillLifecycle.SHADOW, SkillLifecycle.CANARY, SkillLifecycle.ACTIVE):
        good.transition(skill.skill_id, skill.version, state)
    assert good.invalidate({"model-v1"}) == ("verify-payment:1.0.0",)
    assert good.get(skill.skill_id, skill.version).lifecycle is SkillLifecycle.QUARANTINED


def test_promoting_new_skill_version_and_rollback_restore_one_qualified_active_version() -> None:
    registry = SkillRegistry()
    first = _skill()
    second = replace(first, version="2.0.0", parent_version="1.0.0", fingerprint="")
    for skill in (first, second):
        registry.register(skill)
        registry.transition(skill.skill_id, skill.version, SkillLifecycle.SANDBOXED)
        registry.record_evaluation(
            SkillEvaluation(f"eval-{skill.version}", skill.fingerprint, 10, 0.5, 0.8, 0, 1)
        )
        for state in (
            SkillLifecycle.EVALUATED, SkillLifecycle.SHADOW,
            SkillLifecycle.CANARY, SkillLifecycle.ACTIVE,
        ):
            registry.transition(skill.skill_id, skill.version, state)
    assert registry.get(first.skill_id, first.version).lifecycle is SkillLifecycle.ROLLED_BACK
    registry.rollback(second.skill_id, second.version)
    assert registry.get(first.skill_id, first.version).lifecycle is SkillLifecycle.ACTIVE
    assert registry.get(second.skill_id, second.version).lifecycle is SkillLifecycle.ROLLED_BACK


def test_memory_dependency_drift_invalidates_records() -> None:
    memory = GovernedMemory()
    memory.put(_record(dependencies=("model-v1",)))
    assert memory.invalidate_dependencies({"model-v1"}) == ("r1",)
    assert memory.store(MemoryKind.EPISODIC).get("r1", tenant_id="tenant-a") is None


def test_compression_checks_preservation_tenant_and_information_loss() -> None:
    records = (_record("a"), _record("b"))
    result = compress_records(
        records, output_id="summary", summary="payment summary",
        preserved_ids=("a", "b"), maximum_information_loss=0,
    )
    assert result.information_loss == 0
    assert result.record.provenance == ("a", "b")
    with pytest.raises(ValueError, match="information-loss"):
        compress_records(
            records, output_id="lossy", summary="x", preserved_ids=("a",),
            maximum_information_loss=0.1,
        )


def test_transfer_gate_covers_positive_harmful_stale_poisoning_and_continuity() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "transfer_evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert TransferEvaluation(**fixture).passes
    assert not TransferEvaluation(0.2, 0.2, 0, 1, 1).passes


def test_system_snapshot_restores_memory_and_skill_registry() -> None:
    system = DNCSystem()
    system.governed_memory.put(_record())
    skill = _skill()
    system.skill_registry.register(skill)
    snapshot = system.capture_execution_snapshot("phase10")
    system.governed_memory.store(MemoryKind.EPISODIC).delete("r1", tenant_id="tenant-a")
    system.skill_registry.disable(skill.skill_id)
    system.restore_execution_snapshot(snapshot)
    assert system.governed_memory.store(MemoryKind.EPISODIC).get("r1", tenant_id="tenant-a") == _record()
    assert system.skill_registry.get(skill.skill_id, skill.version) == skill

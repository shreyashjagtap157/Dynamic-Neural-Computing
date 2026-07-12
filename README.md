# DNC — Dynamic Neural Computation

A formal specification and Python implementation for researching and developing dynamic neural computing systems.

**Specification**: Baseline v1.0 (Frozen) | **Implementation**: 154 tests passing | **Lint**: clean

## Quick Start

```bash
# Run all tests
python tests/phase1_exit_criteria.py
python tests/test_integration.py
python tests/test_invariant_violations.py
python tests/test_invariant_verifier.py
python tests/test_phase2_planner.py
python tests/test_phase3_observability.py
python tests/test_phase4_production.py
python tests/test_phase5b.py
python tests/test_phase5_providers.py
python tests/test_phase7_distributed.py

# Or run all at once
python -c "
import subprocess
tests=['phase1_exit_criteria.py','test_integration.py','test_invariant_violations.py',
      'test_invariant_verifier.py','test_phase2_planner.py','test_phase3_observability.py',
      'test_phase4_production.py','test_phase5b.py','test_phase5_providers.py','test_phase7_distributed.py']
for t in tests:
    r=subprocess.run(['python','tests/'+t],capture_output=True,text=True)
    lines=[l for l in r.stdout.splitlines() if '/' in l and ('passed' in l or 'PASS' in l)]
    print(lines[-1] if lines else t+' FAILED')
"

# Lint
python -m ruff check src/

# Verify spec (PR-4 compliance)
python tools/fix_refs.py --verify

# Freeze spec (Draft -> Baseline)
python tools/freeze_spec.py
```

## What is DNC?

DNC defines a formal execution model for dynamic neural computation — not neuron-level simulation, but structured computation graphs with formal semantics.

**Core abstraction**: Execution graphs (DAGs) of module instances, analogous to neural circuits. The runtime plans, schedules, and executes these graphs with formal guarantees about invariant preservation, checkpoint/restore, and rollback.

**Key properties**:
- Execution graphs are DAGs (INV-2), not arbitrary graphs
- Module preconditions enforced — upstream must complete before downstream runs (INV-3)
- Single-ownership per module type (INV-4)
- State managed via copy-on-write working memory, append-only history, checkpoints
- O(|V|²) worst-case planner complexity bounds (INV-PLANNER-10)
- Bounded behavioral drift after continual learning updates (INV-CL-10)

## Project Structure

```
src/dnc/
├── runtime/          # Runtime types, Runtime class (Observe→Decide→Act→Assess)
├── state/            # ExecutionState, WorkingMemory, Checkpoint, HistoryLog, Registry
├── scheduler/        # Kahn's algorithm topological sort, runnable detection
├── invariants/       # RuntimeInvariantSet, BootstrapVerifier
├── planner/          # 4-phase planner pipeline (TaskAnalysis→ModuleSelection→GraphConstruction→Validation)
├── cost/             # CostBudget, CostForecaster, StagedCheckpointBudget
├── modules/          # SourceModule, TransformModule, AggregateModule, SinkModule
├── observability/    # ProvenanceLog, FailureClassifier, EvaluationSuite, BiasEvaluationFramework
├── learning/         # DriftChecker, KnowledgeBase, InvariantKB (continual learning)
├── execution/        # DecisionPolicy, ExecutionProvider, ExecutionTrace, ReplayEngine
├── providers/        # OllamaProvider, vLLMProvider, OpenAIProvider, AnthropicProvider, GeminiProvider
├── evaluation/       # ComputationMonitor (DCI, CCG, Budget Elasticity, Graph Entropy...)
└── distributed/      # DistributedCoordinator, IdempotentReceiver, DistributedHandoffConfig
```

## Specification

Formal docs in `specs/`:

| Layer | Topic |
|-------|-------|
| Layer 0 | Governance (16 principles: PR-1 to PR-16) |
| Layer 1 | Vocabulary (authoritative definitions) |
| Layer 2 | Constitution (11 runtime invariants: INV-1 to INV-11) |
| Layer 3 | Semantics (formal model, state management, control loop) |
| Layer 4 | Mechanisms (planner pipeline, scheduler, cost semantics) |
| Layer 5 | Observability (provenance, failure taxonomy, evaluation suite) |
| Layer 6 | Evolution (continual learning, bounded drift) |
| Layer 7 | Distributed (inter-process handoffs, at-least-once delivery) |

**Spec freeze tool**: `tools/freeze_spec.py` — batch-updates all Draft DR-* docs to Baseline v1.0/Frozen.

**Spec verification**: `python tools/fix_refs.py --verify` (PR-4 lower-layers-only rule) and `--rfc2119` (RFC 2119 keyword discipline).

## Implementation Phases

| Phase | Tests | Scope |
|-------|-------|-------|
| Phase 1 | 30 | Core execution engine, module registry, scheduler, invariant enforcement |
| Phase 2 | 9 | Planner pipeline, replanning protocol, control loop, cost semantics |
| Phase 3 | 12 | Provenance, failure taxonomy, evaluation suite, continual learning |
| Phase 4 | 10 | RegressionMonitor, BiasEvaluationFramework (PR-15 fairness metrics) |
| Phase 5B | 20 | DecisionPolicy, ExecutionProvider, ExecutionTrace, ReplayEngine |
| Phase 5C | 17 | Ollama, vLLM, OpenAI, Anthropic, Gemini providers |
| Phase 5D | 17 | ComputationMonitor with DCI, CCG, Budget Elasticity, Graph Entropy... |
| Phase 7 | 22 | DistributedCoordinator, IdempotentReceiver, partition handling, single-hop |

**Total: 154 tests passing**

## Dependencies

```bash
pip install ruff  # linting
```

No other runtime dependencies — pure Python standard library.

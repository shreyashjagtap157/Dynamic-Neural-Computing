# DNC — Dynamic Neural Computation

A formal specification and Python implementation for researching and developing dynamic neural computing systems.

> [!WARNING]
> **Current maturity: conformant research platform.** The implemented architecture
> and complete test suite pass their current gates; empirical state-of-the-art,
> enterprise operations, and end-to-end tensor-native neural execution remain roadmap work. A
> portable neural contract and optional PyTorch adapter now provide the first backend foundation. See
> the [current status](docs/project/REPOSITORY-STATUS.md) for verified results.

## Quick Start

```bash
# Install the package and development tools
python -m pip install -e '.[dev]'

# Run the authoritative test suite
pytest

# Lint
python -m ruff check src/

# Validate and inspect a Generic DNC-IR document
dnc graph validate graph.json
dnc graph inspect graph.json

# Project an admitted graph to an executable DAG
dnc graph project graph.json --output executable.json

# Freeze spec (Draft -> Baseline)
python tools/freeze_spec.py
```

The same CLI is available as `python -m dnc`. Governed graphs require
`--context execution-context.json`; `--structural-only` validates structure without claiming execution
admission. See the [M1 SDK usage guide](docs/project/M1-SDK-USAGE.md) for the Python facade,
content-addressed registries, and fingerprint-pinned plugin boundary.

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

Specification references and normative invariant wording are validated with
`python tools/fix_refs.py --verify` and `python tools/fix_refs.py --rfc2119`.

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

These historical phase counts describe intended scope, not the current test
result. Consult the generated CI result and the
[repository status](docs/project/REPOSITORY-STATUS.md).

## Dependencies

The core currently has no mandatory third-party runtime dependency. Development
dependencies and optional future backend integrations are declared through
`pyproject.toml` extras.

## Project records and roadmap

- [Documentation index](docs/README.md)
- [Current status](docs/project/REPOSITORY-STATUS.md)
- [M1 SDK and plugin usage](docs/project/M1-SDK-USAGE.md)
- [User questions and research assessments](docs/research/USER-QUESTIONS-AND-ASSESSMENTS.md)
- [Enterprise platform roadmap](docs/roadmap/ENTERPRISE-PLATFORM-ROADMAP.md)

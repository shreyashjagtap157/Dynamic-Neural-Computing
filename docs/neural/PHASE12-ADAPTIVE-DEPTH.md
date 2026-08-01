# Phase 12 Neural Adaptive Depth, Routing, and Training

**Status:** Reference implementation locally verified on 2026-08-01; PyTorch numerical qualification pending on a Torch-enabled device

## Work Packages

| Package | Evidence |
|---|---|
| NEU-001 | Frozen `tiny-mlp` / toy-classification experiment design contract |
| NEU-002 | Full-depth baseline identity, dataset hash, seed, and content-addressed checkpoint lineage |
| NEU-003 | Multi-exit architecture executing an observed variable number of layers |
| NEU-004 | Exit loss, full-depth teacher loss, and compute regularization objective |
| NEU-005 | Exit calibration keyed by layer, domain, risk class, and model fingerprint |
| NEU-006 | Capability-registry-qualified execution and `NeuralExitEvidence` export |
| NEU-007 | Forced full-depth fallback and independent runtime kill switch |
| NEU-008 | Matched-quality accuracy/calibration/compute/latency/memory/energy/tail benchmark contract |
| NEU-009 | Shift, stale calibration, adversarial confidence, risk, and batch-isolation tests |
| NEU-010 | PyTorch multi-exit module factory; numerical test is optional-profile gated |
| NEU-011 | Distributed training/sharding intentionally deferred until single-node PyTorch qualification |

## Integration

`DNCSystem.execute_adaptive_neural()` accepts only an active capability explicitly marked for adaptive neural execution. Capability model identity, risk limit, health, lifecycle, expiry, and calibration domain are checked before the model runs. Each exit is recorded with the actual layer trace and compute fraction. Task-level adaptive halting remains a separate Phase 6 decision.

The reference model demonstrates genuine variable layer execution: qualified easy inputs exit at layer 2 of 4, while low confidence, high risk, calibration shift, model drift, forced fallback, or the kill switch execute all four layers.

## Evidence Boundary

Torch is not installed in the current environment. The optional multi-exit `torch.nn.Module` factory and numerical shape test are implemented but the test is skipped locally. Therefore this phase establishes the backend-independent mechanism and reference behavior, not PyTorch performance, training convergence, quantization, compilation, or hardware savings. Those claims require the declared Torch-enabled qualification run.

## Rollback

Set the neural kill switch, force full depth, disable the capability card, or route to the existing full-depth backend. No task-level halting or learned-controller state changes are required.

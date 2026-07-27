# Tensor-native neural backends

## Purpose

DNC's core graph and governance model is framework-independent. The neural profile adds explicit
contracts for tensor shape and dtype, parameters, gradient ownership, compilation, precision,
quantization, cache behavior, and backend compatibility. This lets a structural decision be
validated before a framework executes it.

## Components

- `NeuralUnitContract` describes the portable boundary of a neural unit.
- `NeuralBackend` defines compilation, execution, checkpoint, and restore operations.
- `NeuralBackendRegistry` selects a compatible backend deterministically or by explicit preference.
- `PyTorchBackend` is an optional adapter and loads PyTorch only when instantiated. Install it with
  `pip install -e '.[torch]'`.

The core package does not require PyTorch. Future JAX, ONNX Runtime, TensorRT, and distributed
training adapters should implement the same protocol rather than adding framework behavior to the
governance runtime.

## Current boundary

This is a tested interoperability foundation, not a claim of production-grade model training.
The neural profile is not yet projected from DNC-IR, and it does not yet define optimizer state,
distributed sharding, data pipelines, model artifact formats, or deployment serving semantics.
Those integrations must retain transactional authorization, traceability, replay limitations, and
backend-specific checkpoint guarantees.

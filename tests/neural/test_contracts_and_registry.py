from __future__ import annotations

from typing import Any

import pytest

from dnc.neural import (
    GradientPolicy,
    NeuralBackendRegistry,
    NeuralExecutionRequest,
    NeuralExecutionResult,
    NeuralUnitContract,
    ParameterSpec,
    QuantizationPolicy,
    TensorSpec,
)


class FakeBackend:
    def __init__(self, backend_id: str) -> None:
        self.backend_id = backend_id
        self.saved: Any = None

    def supports(self, contract: NeuralUnitContract) -> bool:
        return not contract.supported_backends or self.backend_id in contract.supported_backends

    def compile(self, unit_id: str, contract: NeuralUnitContract) -> str:
        return f"{self.backend_id}:{unit_id}:{len(contract.inputs)}"

    def execute(
        self, contract: NeuralUnitContract, request: NeuralExecutionRequest
    ) -> NeuralExecutionResult:
        contract.validate()
        return NeuralExecutionResult(request.inputs, backend_id=self.backend_id)

    def checkpoint(self, unit_id: str) -> Any:
        return self.saved

    def restore(self, unit_id: str, checkpoint: Any) -> None:
        self.saved = checkpoint


def contract(**overrides: Any) -> NeuralUnitContract:
    values: dict[str, Any] = {
        "inputs": {"tokens": TensorSpec(("batch", "sequence"), "int64")},
        "outputs": {"hidden": TensorSpec(("batch", "sequence", 8), "float32")},
    }
    values.update(overrides)
    return NeuralUnitContract(**values)


def test_tensor_spec_validates_symbolic_dimensions() -> None:
    spec = TensorSpec(("batch", "sequence", "sequence"), "float32")
    assert spec.validate_shape((2, 4, 4))
    assert not spec.validate_shape((2, 4, 5))
    assert not spec.validate_shape((2, 4))


def test_contract_rejects_invalid_parameter_policies() -> None:
    parameter = ParameterSpec("weight", TensorSpec((8, 8), "float32"))
    with pytest.raises(ValueError, match="frozen"):
        contract(parameters=(parameter,), gradient_policy=GradientPolicy.FROZEN).validate()
    with pytest.raises(ValueError, match="unique"):
        contract(
            parameters=(parameter, parameter), gradient_policy=GradientPolicy.ENABLED
        ).validate()


def test_quantization_policy_rejects_incoherent_configuration() -> None:
    with pytest.raises(ValueError, match="bit width"):
        QuantizationPolicy(mode="none", bits=8)
    with pytest.raises(ValueError, match="unsupported"):
        QuantizationPolicy(mode="integer", bits=7)


def test_registry_selects_deterministically_and_honors_preference() -> None:
    registry = NeuralBackendRegistry()
    registry.register(FakeBackend("zeta"))
    registry.register(FakeBackend("alpha"))
    assert registry.select(contract()).backend_id == "alpha"
    assert registry.select(contract(), preferred="zeta").backend_id == "zeta"
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeBackend("alpha"))


def test_registry_enforces_supported_backends_and_checkpoint_contract() -> None:
    registry = NeuralBackendRegistry()
    backend = FakeBackend("cpu")
    registry.register(backend)
    restricted = contract(supported_backends=frozenset({"accelerator"}))
    with pytest.raises(LookupError, match="no registered"):
        registry.select(restricted)
    backend.restore("unit", {"weight": 1})
    assert backend.checkpoint("unit") == {"weight": 1}

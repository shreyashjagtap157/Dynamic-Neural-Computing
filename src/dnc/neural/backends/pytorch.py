"""Optional PyTorch adapter for DNC neural-unit contracts."""

from __future__ import annotations

import copy
import importlib
from typing import Any

from dnc.neural.contracts import NeuralExecutionRequest, NeuralExecutionResult, NeuralUnitContract


class PyTorchBackend:
    """Execute registered ``torch.nn.Module`` objects without coupling dnc-core to torch."""

    backend_id = "pytorch"

    def __init__(self) -> None:
        self._torch = importlib.import_module("torch")
        self._modules: dict[str, Any] = {}
        self._compiled: dict[str, str] = {}

    def register_module(self, unit_id: str, module: Any) -> None:
        if unit_id in self._modules:
            raise ValueError(f"module already registered: {unit_id}")
        if not isinstance(module, self._torch.nn.Module):
            raise TypeError("module must be an instance of torch.nn.Module")
        self._modules[unit_id] = module

    def supports(self, contract: NeuralUnitContract) -> bool:
        return not contract.supported_backends or self.backend_id in contract.supported_backends

    def compile(self, unit_id: str, contract: NeuralUnitContract) -> str:
        module = self._module(unit_id)
        signature = self._signature(unit_id, contract)
        if contract.compilation_policy.value != "eager" and hasattr(self._torch, "compile"):
            self._modules[unit_id] = self._torch.compile(module)
        self._compiled[unit_id] = signature
        return signature

    def execute(
        self, contract: NeuralUnitContract, request: NeuralExecutionRequest
    ) -> NeuralExecutionResult:
        contract.validate()
        module = self._module(request.unit_id)
        module.train(request.training)
        ordered_inputs = [request.inputs[name] for name in contract.inputs]
        context = self._torch.enable_grad() if request.training else self._torch.no_grad()
        with context:
            raw = module(*ordered_inputs)
        if isinstance(raw, dict):
            outputs = raw
        elif len(contract.outputs) == 1:
            outputs = {next(iter(contract.outputs)): raw}
        else:
            outputs = dict(zip(contract.outputs, raw))
        for name, spec in contract.outputs.items():
            value = outputs[name]
            if hasattr(value, "shape") and not spec.validate_shape(tuple(value.shape)):
                raise ValueError(f"output {name} violates declared tensor shape")
        return NeuralExecutionResult(
            outputs=outputs,
            state=request.state,
            backend_id=self.backend_id,
            compiled_signature=self._compiled.get(request.unit_id),
        )

    def checkpoint(self, unit_id: str) -> Any:
        module = self._module(unit_id)
        return copy.deepcopy(module.state_dict())

    def restore(self, unit_id: str, checkpoint: Any) -> None:
        self._module(unit_id).load_state_dict(copy.deepcopy(checkpoint))

    def _module(self, unit_id: str) -> Any:
        try:
            return self._modules[unit_id]
        except KeyError as error:
            raise KeyError(f"no PyTorch module registered for {unit_id}") from error

    @staticmethod
    def _signature(unit_id: str, contract: NeuralUnitContract) -> str:
        inputs = ",".join(f"{name}:{spec.shape}:{spec.dtype}" for name, spec in contract.inputs.items())
        return f"pytorch:{unit_id}:{inputs}:{contract.precision}:{contract.quantization.mode}"

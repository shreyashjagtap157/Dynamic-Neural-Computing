"""Neural backend protocol and deterministic backend selection."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dnc.neural.contracts import NeuralExecutionRequest, NeuralExecutionResult, NeuralUnitContract


@runtime_checkable
class NeuralBackend(Protocol):
    @property
    def backend_id(self) -> str: ...

    def supports(self, contract: NeuralUnitContract) -> bool: ...

    def compile(self, unit_id: str, contract: NeuralUnitContract) -> str: ...

    def execute(
        self, contract: NeuralUnitContract, request: NeuralExecutionRequest
    ) -> NeuralExecutionResult: ...

    def checkpoint(self, unit_id: str) -> Any: ...

    def restore(self, unit_id: str, checkpoint: Any) -> None: ...


class NeuralBackendRegistry:
    """Version-independent registry that rejects ambiguous backend ownership."""

    def __init__(self) -> None:
        self._backends: dict[str, NeuralBackend] = {}

    def register(self, backend: NeuralBackend) -> None:
        if backend.backend_id in self._backends:
            raise ValueError(f"neural backend already registered: {backend.backend_id}")
        self._backends[backend.backend_id] = backend

    def get(self, backend_id: str) -> NeuralBackend:
        try:
            return self._backends[backend_id]
        except KeyError as error:
            raise KeyError(f"unknown neural backend: {backend_id}") from error

    def select(self, contract: NeuralUnitContract, preferred: str | None = None) -> NeuralBackend:
        if preferred is not None:
            backend = self.get(preferred)
            if not backend.supports(contract):
                raise ValueError(f"backend {preferred} does not support the neural contract")
            return backend
        matches = [backend for backend in self._backends.values() if backend.supports(contract)]
        if not matches:
            raise LookupError("no registered neural backend supports the contract")
        return sorted(matches, key=lambda item: item.backend_id)[0]

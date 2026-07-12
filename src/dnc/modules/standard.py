"""Standard module types for Phase 1 testing: SOURCE, TRANSFORM, AGGREGATE, SINK, FAULT_INJECTOR."""

from __future__ import annotations

from typing import Any

from dnc.modules.base import BaseModule
from dnc.runtime.types import (
    ModuleTypeID,
    ModuleContract,
    PENDING,
)


class SourceModule(BaseModule):
    """Produces data without requiring input. Zero upstream edges.

    Output is produced immediately on first observe() call with a default value.
    """

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
        output_value: Any = 1,
    ) -> None:
        super().__init__(instance_id, contract)
        self._output_value = output_value
        self._invoked = False

    def observe(self, input_value: Any) -> Any:
        if self._invoked:
            return self._output_value
        self._invoked = True
        return self._output_value


class TransformModule(BaseModule):
    """Applies a function to its input and produces output.

    Precondition: upstream buffer must be COMPLETE (output not UNBOUND/PENDING).
    """

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
        transform_fn: Any = None,
    ) -> None:
        super().__init__(instance_id, contract)
        self._transform_fn = transform_fn or (lambda x: x * 2)

    def observe(self, input_value: Any) -> Any:
        return self._transform_fn(input_value)


class AggregateModule(BaseModule):
    """Combines inputs from multiple upstream modules using a reduce function.

    Waits until all inputs are bound, then applies the reduce function.
    """

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
        reduce_fn: Any = None,
    ) -> None:
        super().__init__(instance_id, contract)
        self._reduce_fn = reduce_fn or (lambda inputs: sum(inputs) if inputs else 0)

    def observe(self, input_value: Any) -> Any:
        if not isinstance(input_value, list):
            input_value = [input_value]
        return self._reduce_fn(input_value)


class SinkModule(BaseModule):
    """Consumes data without producing output for downstream. Terminal node."""

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
        accumulator: Any = None,
    ) -> None:
        super().__init__(instance_id, contract)
        self._accumulator = accumulator

    def observe(self, input_value: Any) -> Any:
        self._accumulator = input_value
        return None


class FaultInjectorModule(BaseModule):
    """Injects failures for testing fault-tolerance scenarios.

    Per failure-taxonomy.md: INVALID_OUTPUT, GPU_RECOVERY, PARTIAL_FAILURE.
    """

    class FaultMode:
        INVALID_OUTPUT = "INVALID_OUTPUT"
        GPU_RECOVERY = "GPU_RECOVERY"
        PARTIAL_FAILURE = "PARTIAL_FAILURE"

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
        fault_mode: str = FaultMode.INVALID_OUTPUT,
        fault_after: int = 0,
    ) -> None:
        super().__init__(instance_id, contract)
        self._fault_mode = fault_mode
        self._invocation_count = 0
        self._fault_after = fault_after

    def observe(self, input_value: Any) -> Any:
        self._invocation_count += 1
        if self._invocation_count > self._fault_after:
            if self._fault_mode == self.FaultMode.INVALID_OUTPUT:
                return "<INVALID_OUTPUT>"
            elif self._fault_mode == self.FaultMode.GPU_RECOVERY:
                return PENDING()
            elif self._fault_mode == self.FaultMode.PARTIAL_FAILURE:
                return None
        return input_value
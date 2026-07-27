"""Base module interface and contract validation.

Per module-lifecycle.md and INV-4: every module type has exactly one
owning document in the registry. Contracts are validated on registration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from dnc.runtime.types import (
    Buffer,
    ModuleTypeID,
    ModuleContract,
    UNBOUND,
    PENDING,
)


class BaseModule(ABC):
    """Abstract base class for all DNC module implementations.

    Subclass this and implement observe() to create a module type.
    Register instances via the runtime's module registry.
    """

    def __init__(
        self,
        instance_id: ModuleTypeID,
        contract: ModuleContract,
    ) -> None:
        self._instance_id = instance_id
        self._contract = contract

    @property
    def instance_id(self) -> ModuleTypeID:
        return self._instance_id

    @property
    def contract(self) -> ModuleContract:
        return self._contract

    @abstractmethod
    def observe(self, input_value: Any) -> Any:
        """Process input and return output.

        Return PENDING() if the module cannot produce output yet.
        Return UNBOUND() to indicate no input was valid.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._instance_id.name}>"


def validate_contract(contract: ModuleContract) -> None:
    """Validate a module contract on registration. Raises ValueError if invalid."""
    if not isinstance(contract.module_type_id, ModuleTypeID):
        raise ValueError(
            f"contract.module_type_id must be ModuleTypeID, got {type(contract.module_type_id)}"
        )
    if not isinstance(contract.output_signature, type):
        raise ValueError(
            f"contract.output_signature must be a type, got {type(contract.output_signature)}"
        )
    if not isinstance(contract.capabilities, frozenset):
        raise ValueError(
            f"contract.capabilities must be frozenset, got {type(contract.capabilities)}"
        )
    if contract.cost_weight <= 0:
        raise ValueError(
            f"contract.cost_weight must be positive, got {contract.cost_weight}"
        )
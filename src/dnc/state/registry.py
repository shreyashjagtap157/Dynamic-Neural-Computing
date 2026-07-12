"""Module registry M(t): maps ModuleTypeID to contract declarations.

Per state-management.md DEF-3: M(t) is the registry tracking all module type
declarations, capability annotations, and version constraints.
"""

from typing import Dict, Optional

from dnc.runtime.types import ModuleTypeID, ModuleContract


class ModuleRegistry:
    """Registry of module type declarations.

    Per state-management.md DEF-3: The registry is a total function from
    ModuleTypeID to ModuleContract, with at most one contract per type ID
    (enforced by INV-4/Single-Ownership Rule).
    """

    def __init__(self) -> None:
        self._contracts: Dict[ModuleTypeID, ModuleContract] = {}
        self._type_id_index: Dict[str, ModuleTypeID] = {}

    def register(self, contract: ModuleContract) -> None:
        """Register a module contract. Raises ValueError if type_id already has a contract."""
        type_id = contract.module_type_id
        if type_id in self._contracts:
            raise ValueError(
                f"ModuleTypeID {type_id} already registered. "
                f"INV-4 violation: one document per module type."
            )
        self._contracts[type_id] = contract
        self._type_id_index[type_id.name] = type_id

    def get(self, type_id: ModuleTypeID) -> ModuleContract:
        """Return the contract for a module type ID, or raise KeyError."""
        if type_id not in self._contracts:
            raise KeyError(f"ModuleTypeID {type_id} not found in registry")
        return self._contracts[type_id]

    def get_by_name(self, name: str) -> ModuleContract:
        """Look up a contract by module name."""
        if name not in self._type_id_index:
            raise KeyError(f"Module name '{name}' not found in registry")
        return self._contracts[self._type_id_index[name]]

    def find(self, type_id: ModuleTypeID) -> Optional[ModuleContract]:
        """Return contract if found, else None."""
        return self._contracts.get(type_id)

    def __contains__(self, type_id: ModuleTypeID) -> bool:
        return type_id in self._contracts

    def __len__(self) -> int:
        return len(self._contracts)

    def list_all(self) -> Dict[ModuleTypeID, ModuleContract]:
        """Return a copy of all registered contracts."""
        return dict(self._contracts)

    def snapshot(self) -> Dict[str, dict]:
        """Return a serializable dict snapshot for ES(t) storage."""
        result = {}
        for type_id, contract in self._contracts.items():
            result[type_id.name] = {
                "type_id": {
                    "name": type_id.name,
                    "contract_hash": type_id.contract_hash,
                },
                "input_signature": contract.input_signature,
                "output_signature": (
                    contract.output_signature.__name__
                    if isinstance(contract.output_signature, type)
                    else str(contract.output_signature)
                ),
                "capabilities": sorted(contract.capabilities),
                "cost_weight": contract.cost_weight,
            }
        return result
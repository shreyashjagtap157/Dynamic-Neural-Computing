"""Optional PyTorch snapshot helpers for Phase 2."""

from __future__ import annotations

import copy
import importlib.util
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TorchSnapshot:
    """Captured PyTorch module and RNG state."""

    module_state: Any
    cpu_rng_state: Any
    cuda_rng_state: Any | None = None
    optimizer_state: Any | None = None
    scheduler_state: Any | None = None
    scaler_state: Any | None = None
    sampler_state: Any | None = None
    code_fingerprint: str | None = None
    config_fingerprint: str | None = None


def torch_available() -> bool:
    """Return whether PyTorch is importable in the active environment."""

    return importlib.util.find_spec("torch") is not None


class PyTorchSnapshotManager:
    """Snapshot and restore a torch module plus RNG state when torch exists."""

    def __init__(self) -> None:
        if not torch_available():
            raise RuntimeError("PyTorch is not installed")
        import torch

        self._torch = torch

    def capture_module(
        self,
        module: Any,
        *,
        optimizer: Any | None = None,
        scheduler: Any | None = None,
        scaler: Any | None = None,
        sampler: Any | None = None,
        code_fingerprint: str | None = None,
        config_fingerprint: str | None = None,
    ) -> TorchSnapshot:
        if not isinstance(module, self._torch.nn.Module):
            raise TypeError("module must be an instance of torch.nn.Module")
        cuda_state = None
        if self._torch.cuda.is_available():
            cuda_state = self._torch.cuda.get_rng_state_all()
        return TorchSnapshot(
            module_state=copy.deepcopy(module.state_dict()),
            cpu_rng_state=copy.deepcopy(self._torch.random.get_rng_state()),
            cuda_rng_state=copy.deepcopy(cuda_state),
            optimizer_state=self._state_dict(optimizer),
            scheduler_state=self._state_dict(scheduler),
            scaler_state=self._state_dict(scaler),
            sampler_state=self._sampler_state(sampler),
            code_fingerprint=code_fingerprint,
            config_fingerprint=config_fingerprint,
        )

    def restore_module(
        self,
        module: Any,
        snapshot: TorchSnapshot,
        *,
        optimizer: Any | None = None,
        scheduler: Any | None = None,
        scaler: Any | None = None,
        sampler: Any | None = None,
    ) -> None:
        if not isinstance(module, self._torch.nn.Module):
            raise TypeError("module must be an instance of torch.nn.Module")
        module.load_state_dict(copy.deepcopy(snapshot.module_state))
        self._torch.random.set_rng_state(copy.deepcopy(snapshot.cpu_rng_state))
        if snapshot.cuda_rng_state is not None and self._torch.cuda.is_available():
            self._torch.cuda.set_rng_state_all(copy.deepcopy(snapshot.cuda_rng_state))
        self._restore_state_dict("optimizer", optimizer, snapshot.optimizer_state)
        self._restore_state_dict("scheduler", scheduler, snapshot.scheduler_state)
        self._restore_state_dict("scaler", scaler, snapshot.scaler_state)
        if snapshot.sampler_state is not None:
            if sampler is None:
                raise ValueError("sampler is required to restore captured sampler state")
            if hasattr(sampler, "load_state_dict"):
                sampler.load_state_dict(copy.deepcopy(snapshot.sampler_state))
            elif hasattr(sampler, "position"):
                sampler.position = copy.deepcopy(snapshot.sampler_state)
            else:
                raise TypeError("sampler must expose load_state_dict() or position")

    @staticmethod
    def _state_dict(component: Any | None) -> Any | None:
        if component is None:
            return None
        if not hasattr(component, "state_dict"):
            raise TypeError("training components must expose state_dict()")
        return copy.deepcopy(component.state_dict())

    @staticmethod
    def _sampler_state(sampler: Any | None) -> Any | None:
        if sampler is None:
            return None
        if hasattr(sampler, "state_dict"):
            return copy.deepcopy(sampler.state_dict())
        if hasattr(sampler, "position"):
            return copy.deepcopy(sampler.position)
        raise TypeError("sampler must expose state_dict() or position")

    @staticmethod
    def _restore_state_dict(name: str, component: Any | None, state: Any | None) -> None:
        if state is None:
            return
        if component is None:
            raise ValueError(f"{name} is required to restore captured {name} state")
        if not hasattr(component, "load_state_dict"):
            raise TypeError(f"{name} must expose load_state_dict()")
        component.load_state_dict(copy.deepcopy(state))

"""Optional neural framework adapters."""

from dnc.neural.backends.pytorch import PyTorchBackend
from dnc.neural.backends.adaptive_pytorch import build_pytorch_early_exit_module

__all__ = ["PyTorchBackend", "build_pytorch_early_exit_module"]

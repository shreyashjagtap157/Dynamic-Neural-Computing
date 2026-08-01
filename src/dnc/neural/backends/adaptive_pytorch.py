"""Optional PyTorch multi-exit model factory for Phase 12 qualification."""

from __future__ import annotations

import importlib


def build_pytorch_early_exit_module(
    *, input_size: int, hidden_size: int, classes: int, depth: int, exit_layers: tuple[int, ...]
):
    torch = importlib.import_module("torch")
    if depth <= 0 or exit_layers[-1] != depth or any(layer <= 0 or layer > depth for layer in exit_layers):
        raise ValueError("PyTorch exit layers MUST be valid and terminate at full depth")

    class PyTorchEarlyExitModule(torch.nn.Module):
        def __init__(self):
            super().__init__()
            layers = []
            for index in range(depth):
                layers.append(torch.nn.Linear(input_size if index == 0 else hidden_size, hidden_size))
            self.layers = torch.nn.ModuleList(layers)
            self.exit_heads = torch.nn.ModuleDict(
                {str(layer): torch.nn.Linear(hidden_size, classes) for layer in exit_layers}
            )

        def forward(self, inputs):
            hidden = inputs
            outputs = {}
            for layer_number, layer in enumerate(self.layers, start=1):
                hidden = torch.relu(layer(hidden))
                if str(layer_number) in self.exit_heads:
                    outputs[str(layer_number)] = self.exit_heads[str(layer_number)](hidden)
            return outputs

    return PyTorchEarlyExitModule()

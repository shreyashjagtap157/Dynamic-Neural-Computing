"""Content-addressed object store with tenant ACL and integrity verification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class ContentAddressedObjectStore:
    _objects: dict[tuple[str, str], bytes] = field(default_factory=dict)

    def put(self, data: bytes, *, tenant_id: str) -> str:
        digest = hashlib.sha256(data).hexdigest()
        self._objects[(tenant_id, digest)] = bytes(data)
        return digest

    def get(self, digest: str, *, tenant_id: str) -> bytes:
        try:
            data = self._objects[(tenant_id, digest)]
        except KeyError as error:
            raise KeyError("unknown tenant-scoped object") from error
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("object integrity verification failed")
        return bytes(data)

    def corrupt_for_test(self, digest: str, *, tenant_id: str, data: bytes) -> None:
        self._objects[(tenant_id, digest)] = data

    def snapshot(self) -> dict[tuple[str, str], bytes]:
        return {key: bytes(value) for key, value in self._objects.items()}

    def restore(self, state: dict[tuple[str, str], bytes]) -> None:
        for (tenant_id, digest), data in state.items():
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("backup object integrity verification failed")
            if not tenant_id:
                raise ValueError("backup object tenant MUST be non-empty")
        self._objects = {key: bytes(value) for key, value in state.items()}

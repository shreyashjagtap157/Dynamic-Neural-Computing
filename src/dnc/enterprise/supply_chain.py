"""Release artifact identity, signature metadata, and SBOM records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SignedArtifact:
    artifact_id: str
    digest: str
    signer: str
    signature: str
    provenance_ref: str

    def verify_digest(self, payload: bytes) -> bool:
        return hashlib.sha256(payload).hexdigest() == self.digest

    def verify(
        self,
        payload: bytes,
        signature_verifier: Callable[[str, str, str], bool],
    ) -> bool:
        return self.verify_digest(payload) and signature_verifier(
            self.signer, self.digest, self.signature
        )


@dataclass(frozen=True)
class SBOM:
    project: str
    version: str
    components: tuple[str, ...]
    generated_by: str

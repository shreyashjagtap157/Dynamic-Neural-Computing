"""Protocol boundaries for Phase 1 kernel extension points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Clock(Protocol):
    """Clock interface for deterministic and wall-clock runtimes."""

    def now_ns(self) -> int:
        """Return current time in nanoseconds."""


class IDProvider(Protocol):
    """Stable ID generation interface."""

    def new_id(self, prefix: str) -> str:
        """Return a new ID with the requested prefix."""


class HashProvider(Protocol):
    """Hashing interface for canonical state and artifacts."""

    def sha256_text(self, value: str) -> str:
        """Return SHA-256 hex digest for text."""


class RandomnessProvider(Protocol):
    """Randomness interface so deterministic runs can inject seeded sources."""

    def random_float(self) -> float:
        """Return a float in the half-open interval [0.0, 1.0)."""


@dataclass(frozen=True)
class Deadline:
    """Absolute deadline in nanoseconds for cancellable work."""

    deadline_ns: int

    def expired(self, clock: Clock) -> bool:
        """Return whether the deadline has passed according to a clock."""

        return clock.now_ns() >= self.deadline_ns


class CancellationToken(Protocol):
    """Cancellation interface shared by runtimes, providers, and cleanup."""

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested."""


class ArtifactStore(Protocol):
    """Artifact persistence boundary for packages, traces, and reports."""

    def put_bytes(self, artifact_id: str, payload: bytes) -> str:
        """Persist bytes and return a content hash or URI."""

    def get_bytes(self, artifact_id: str) -> bytes:
        """Load bytes for an artifact ID."""

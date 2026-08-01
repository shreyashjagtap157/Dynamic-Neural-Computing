"""DNC kernel error taxonomy."""


class DNCError(Exception):
    """Base class for DNC kernel and cognitive-runtime errors."""


class DNCValidationError(DNCError):
    """Invalid schema, state, invariant, operation, or contract."""


class DNCPolicyError(DNCError):
    """Authorization, governance, safety, tenant, or policy violation."""


class DNCCapabilityError(DNCError):
    """Capability is unavailable, degraded, unsupported, or misconfigured."""


class DNCRetryableTransportError(DNCError):
    """Retryable provider, network, rate-limit, timeout, or transport failure."""


class DNCExecutionError(DNCError):
    """Execution failed after authorization and dispatch."""


class DNCVerificationError(DNCError):
    """Verifier failed, is inapplicable, or returned inconsistent evidence."""


class DNCCalibrationError(DNCError):
    """Calibration profile, domain, version, or applicability is invalid."""


class DNCCancellationError(DNCError):
    """Operation was cancelled or exceeded a deadline."""


class DNCCleanupError(DNCError):
    """Cleanup, rollback, compensation, or artifact deletion failed."""


class DNCIncidentError(DNCError):
    """Security, privacy, integrity, or operational incident."""

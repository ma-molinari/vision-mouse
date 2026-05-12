from __future__ import annotations


class ApplicationError(RuntimeError):
    """Base exception for application-layer orchestration failures."""


class BoundaryError(ApplicationError):
    """Raised when an application boundary cannot complete its contract."""


class InfrastructureError(BoundaryError):
    """Raised by infrastructure adapters used through application ports."""

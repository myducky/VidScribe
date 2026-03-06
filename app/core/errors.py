from __future__ import annotations


class DomainError(Exception):
    """Base error for predictable application-level failures."""


class InvalidMediaError(DomainError):
    """Raised when an uploaded file is not a valid or supported media input."""

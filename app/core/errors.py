from __future__ import annotations


class DomainError(Exception):
    """Base error for predictable application-level failures."""


class InvalidMediaError(DomainError):
    """Raised when an uploaded file is not a valid or supported media input."""


class EmptyTranscriptError(InvalidMediaError):
    """Raised when transcription completes without producing usable text."""


class LLMUnavailableError(DomainError):
    """Raised when the configured LLM cannot serve requests."""


class RemoteVideoDownloadError(DomainError):
    """Raised when a remote video cannot be downloaded and no fallback input is available."""

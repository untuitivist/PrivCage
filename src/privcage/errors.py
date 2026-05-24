from __future__ import annotations


class PrivCageError(Exception):
    """Base exception for expected PrivCage failures."""


class ParseError(PrivCageError):
    """Raised when a source file cannot be parsed."""


class ConfigError(PrivCageError):
    """Raised when configuration or key loading fails."""

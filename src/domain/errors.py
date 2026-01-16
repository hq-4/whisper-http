from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class DiarizationProcessError(TranscriptError):
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class DiarizationFailure(TranscriptError):
    """Raised when both diarization and fallback pipelines fail."""


class InvalidInputError(TranscriptError):
    """Raised when request validation fails."""

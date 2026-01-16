from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.domain.models import Transcript


class DiarizationRunner(Protocol):
    def run(self, audio_path: Path, timeout: float | None = None) -> "DiarizationRunResult":
        ...


class TranscriptParser(Protocol):
    def parse(self, srt_path: Path) -> Transcript:
        ...


class FallbackTranscriber(Protocol):
    def transcribe(self, audio_path: Path, timeout: float | None = None) -> Transcript:
        ...


class TranscriptSRTSerializer(Protocol):
    def write(self, transcript: Transcript, audio_path: Path) -> Path:
        ...


class Clock(Protocol):
    def monotonic(self) -> float:
        ...


class DiarizationRunResult(Protocol):
    @property
    def ok(self) -> bool:
        ...

    @property
    def srt_path(self) -> Path | None:
        ...

    @property
    def stdout(self) -> str:
        ...

    @property
    def stderr(self) -> str:
        ...

    @property
    def returncode(self) -> int:
        ...

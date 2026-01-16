from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class TranscriptProvenance(str, Enum):
    DIARIZATION = "diarization"
    FASTER_WHISPER = "faster_whisper"


@dataclass(frozen=True)
class Segment:
    sequence: int
    speaker: str
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptMetadata:
    total_duration: float
    speaker_count: int
    provenance: TranscriptProvenance


@dataclass(frozen=True)
class Transcript:
    segments: List[Segment]
    metadata: TranscriptMetadata

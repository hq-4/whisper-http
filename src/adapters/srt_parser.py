from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import srt

from src.domain.models import Segment, Transcript, TranscriptMetadata, TranscriptProvenance
from src.usecases.ports import TranscriptParser


@dataclass(frozen=True)
class _ParsedSegment:
    sequence: int
    speaker: str
    start: float
    end: float
    text: str


class SRTTranscriptParser(TranscriptParser):
    def parse(self, srt_path: Path) -> Transcript:
        with srt_path.open("r", encoding="utf-8-sig") as handle:
            content = handle.read()

        entries = list(srt.parse(content))
        segments = self._build_segments(entries)
        speakers = {segment.speaker for segment in segments}
        total_duration = max((segment.end for segment in segments), default=0.0)

        metadata = TranscriptMetadata(
            total_duration=total_duration,
            speaker_count=len(speakers),
            provenance=TranscriptProvenance.DIARIZATION,
        )
        return Transcript(segments=segments, metadata=metadata)

    @staticmethod
    def _build_segments(entries: Iterable[srt.Subtitle]) -> List[Segment]:
        built: List[Segment] = []
        for entry in entries:
            text = entry.content.strip()
            if not text:
                continue
            speaker, clean_text = _extract_speaker(text)
            built.append(
                Segment(
                    sequence=len(built) + 1,
                    speaker=speaker,
                    start=entry.start.total_seconds(),
                    end=entry.end.total_seconds(),
                    text=clean_text,
                )
            )
        return built


def _extract_speaker(raw_text: str) -> tuple[str, str]:
    if ":" in raw_text:
        prefix, remainder = raw_text.split(":", 1)
        prefix = prefix.strip()
        if prefix.lower().startswith("speaker"):
            return prefix, remainder.strip()
    return "Speaker 0", raw_text

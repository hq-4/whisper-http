from __future__ import annotations

from pathlib import Path
from typing import Iterable

from faster_whisper import WhisperModel

from src.domain.models import Segment, Transcript, TranscriptMetadata, TranscriptProvenance
from src.usecases.ports import FallbackTranscriber


class FasterWhisperFallbackTranscriber(FallbackTranscriber):
    def __init__(
        self,
        model_name: str,
        device: str | None = None,
        language: str | None = None,
        compute_type: str = "auto",
    ) -> None:
        whispered_device = device or "auto"
        self._model = WhisperModel(
            model_name,
            device=whispered_device,
            compute_type=compute_type,
        )
        self._language = language if language else None

    def transcribe(self, audio_path: Path, timeout: float | None = None) -> Transcript:
        # faster-whisper handles streaming internally; we ignore timeout due to lack of native support
        segments_iter, _info = self._model.transcribe(
            str(audio_path),
            language=self._language,
            vad_filter=True,
        )

        segments = list(self._build_segments(segments_iter))
        total_duration = max((segment.end for segment in segments), default=0.0)

        metadata = TranscriptMetadata(
            total_duration=total_duration,
            speaker_count=0,
            provenance=TranscriptProvenance.FASTER_WHISPER,
        )
        return Transcript(segments=segments, metadata=metadata)

    @staticmethod
    def _build_segments(raw_segments: Iterable) -> Iterable[Segment]:
        for index, segment in enumerate(raw_segments, start=1):
            start = float(getattr(segment, "start", 0.0) or 0.0)
            end = float(getattr(segment, "end", start) or start)
            text = (getattr(segment, "text", "") or "").strip()
            if not text:
                continue
            yield Segment(
                sequence=index,
                speaker="Speaker 0",
                start=start,
                end=end,
                text=text,
            )

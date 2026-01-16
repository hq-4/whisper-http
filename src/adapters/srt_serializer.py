from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import srt

from src.domain.models import Transcript


class TranscriptSRTSerializer:
    def write(self, transcript: Transcript, audio_path: Path) -> Path:
        target_path = audio_path.with_suffix(".srt")
        subtitles = []
        for position, segment in enumerate(transcript.segments, start=1):
            text = segment.text.strip()
            if not text:
                continue
            start_seconds = max(float(segment.start), 0.0)
            end_seconds = max(float(segment.end), start_seconds)
            if end_seconds <= start_seconds:
                end_seconds = start_seconds + 0.01

            subtitles.append(
                srt.Subtitle(
                    index=len(subtitles) + 1,
                    start=timedelta(seconds=start_seconds),
                    end=timedelta(seconds=end_seconds),
                    content=f"{segment.speaker}: {text}".strip(),
                    proprietary=f"source_sequence={position}",
                )
            )

        payload = srt.compose(subtitles)
        target_path.write_text(payload, encoding="utf-8-sig")
        logging.getLogger(__name__).info(
            "Persisted transcript to SRT",
            extra={
                "audio_path": str(audio_path),
                "srt_path": str(target_path),
                "segment_count": len(subtitles),
            },
        )
        return target_path

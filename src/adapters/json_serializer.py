from __future__ import annotations

import json
from pathlib import Path

from src.domain.models import Transcript
from src.framework.config import JSON_OUTPUT_EXTENSION


class TranscriptJSONSerializer:
    def to_dict(self, transcript: Transcript) -> dict:
        return {
            "provenance": transcript.metadata.provenance.value,
            "total_duration": transcript.metadata.total_duration,
            "speaker_count": transcript.metadata.speaker_count,
            "segments": [
                {
                    "sequence": segment.sequence,
                    "speaker": segment.speaker,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                }
                for segment in transcript.segments
            ],
        }

    def write(self, transcript: Transcript, audio_path: Path) -> Path:
        target_path = audio_path.with_suffix(JSON_OUTPUT_EXTENSION)
        payload = self.to_dict(transcript)
        target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target_path

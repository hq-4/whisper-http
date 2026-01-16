from __future__ import annotations

from pathlib import Path

from src.adapters.json_serializer import TranscriptJSONSerializer
from src.domain.models import Segment, Transcript, TranscriptMetadata, TranscriptProvenance


def test_serializer_writes_expected_structure(tmp_path: Path) -> None:
    transcript = Transcript(
        segments=[
            Segment(sequence=1, speaker="Speaker 1", start=0.0, end=1.5, text="Hello"),
            Segment(sequence=2, speaker="Speaker 2", start=1.5, end=3.0, text="World"),
        ],
        metadata=TranscriptMetadata(
            total_duration=3.0,
            speaker_count=2,
            provenance=TranscriptProvenance.DIARIZATION,
        ),
    )

    serializer = TranscriptJSONSerializer()
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"")

    json_path = serializer.write(transcript, audio_path)
    payload = serializer.to_dict(transcript)

    assert json_path.exists()
    assert payload["provenance"] == "diarization"
    assert payload["total_duration"] == 3.0
    assert payload["speaker_count"] == 2
    assert len(payload["segments"]) == 2
    assert payload["segments"][0]["speaker"] == "Speaker 1"

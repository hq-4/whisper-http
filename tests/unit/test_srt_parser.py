from __future__ import annotations

from pathlib import Path

from src.adapters.srt_parser import SRTTranscriptParser
from src.domain.models import TranscriptProvenance


def test_parse_extracts_speaker_and_metadata(tmp_path: Path) -> None:
    srt_content = """1\n00:00:00,000 --> 00:00:01,000\nSpeaker 2: Hello there\n\n2\n00:00:01,000 --> 00:00:02,500\nNo speaker prefix text\n"""
    srt_file = tmp_path / "sample.srt"
    srt_file.write_text(srt_content, encoding="utf-8")

    parser = SRTTranscriptParser()
    transcript = parser.parse(srt_file)

    assert transcript.metadata.provenance is TranscriptProvenance.DIARIZATION
    assert transcript.metadata.speaker_count == 2
    assert transcript.metadata.total_duration == 2.5

    assert len(transcript.segments) == 2
    assert transcript.segments[0].speaker == "Speaker 2"
    assert transcript.segments[0].text == "Hello there"
    assert transcript.segments[1].speaker == "Speaker 0"
    assert transcript.segments[1].text == "No speaker prefix text"

from __future__ import annotations

from pathlib import Path

import srt

from src.adapters.srt_parser import SRTTranscriptParser
from src.adapters.srt_serializer import TranscriptSRTSerializer
from src.domain.models import Segment, Transcript, TranscriptMetadata, TranscriptProvenance


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


def test_srt_serializer_merges_duplicate_segments(tmp_path: Path) -> None:
    transcript = Transcript(
        segments=[
            Segment(sequence=1, speaker="Speaker 1", start=0.0, end=2.0, text="Hello world"),
            Segment(sequence=2, speaker="Speaker 1", start=2.0, end=4.0, text="Hello   world"),
            Segment(sequence=3, speaker="Speaker 1", start=4.0, end=5.0, text="Different text"),
        ],
        metadata=TranscriptMetadata(
            total_duration=5.0,
            speaker_count=1,
            provenance=TranscriptProvenance.DIARIZATION,
        ),
    )

    serializer = TranscriptSRTSerializer()
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"")

    srt_path = serializer.write(transcript, audio_path)
    subtitles = list(srt.parse(srt_path.read_text(encoding="utf-8-sig")))

    assert len(subtitles) == 2
    assert subtitles[0].content == "Speaker 1: Hello world"
    assert int(subtitles[0].start.total_seconds()) == 0
    assert int(subtitles[0].end.total_seconds()) == 4
    assert subtitles[1].content == "Speaker 1: Different text"


def test_srt_serializer_strips_speaker_zero_for_fallback(tmp_path: Path) -> None:
    transcript = Transcript(
        segments=[
            Segment(sequence=1, speaker="Speaker 0", start=0.0, end=1.0, text="  repeated line "),
            Segment(sequence=2, speaker="Speaker 0", start=1.0, end=2.5, text="repeated line"),
            Segment(sequence=3, speaker="Speaker 0", start=2.5, end=3.5, text="Second sentence"),
        ],
        metadata=TranscriptMetadata(
            total_duration=3.5,
            speaker_count=0,
            provenance=TranscriptProvenance.FASTER_WHISPER,
        ),
    )

    serializer = TranscriptSRTSerializer()
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"")

    srt_path = serializer.write(transcript, audio_path)
    subtitles = list(srt.parse(srt_path.read_text(encoding="utf-8-sig")))

    assert len(subtitles) == 2
    assert subtitles[0].content == "repeated line"
    assert int(subtitles[0].end.total_seconds()) == 2
    assert subtitles[1].content == "Second sentence"


def test_srt_serializer_splits_long_segments(tmp_path: Path) -> None:
    transcript = Transcript(
        segments=[
            Segment(sequence=1, speaker="Speaker 0", start=0.0, end=120.0, text="looped bumper"),
        ],
        metadata=TranscriptMetadata(
            total_duration=120.0,
            speaker_count=0,
            provenance=TranscriptProvenance.FASTER_WHISPER,
        ),
    )

    serializer = TranscriptSRTSerializer()
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"")

    srt_path = serializer.write(transcript, audio_path)
    subtitles = list(srt.parse(srt_path.read_text(encoding="utf-8-sig")))

    # Should be split into 30-second slices (last one shorter)
    assert len(subtitles) == 4
    durations = [sub.end.total_seconds() - sub.start.total_seconds() for sub in subtitles]
    assert durations[:3] == [30.0, 30.0, 30.0]
    assert durations[3] == 30.0  # 120 / 30 => four equal slices
    assert all(sub.content == "looped bumper" for sub in subtitles)

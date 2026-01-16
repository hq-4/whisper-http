from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from src.domain.errors import DiarizationFailure, InvalidInputError
from src.domain.models import Segment, Transcript, TranscriptMetadata, TranscriptProvenance
from src.usecases.transcription_service import TranscriptionConfig, TranscriptionService


@dataclass
class _FakeRunResult:
    ok: bool
    srt_path: Optional[Path]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class _FakeRunner:
    def __init__(self, result: _FakeRunResult) -> None:
        self._result = result
        self.invocations = 0

    def run(self, audio_path: Path, timeout: float | None = None):
        self.invocations += 1
        return self._result


class _FakeParser:
    def __init__(self, transcript: Transcript) -> None:
        self._transcript = transcript
        self.invocations = 0

    def parse(self, srt_path: Path) -> Transcript:
        self.invocations += 1
        return self._transcript


class _FakeFallback:
    def __init__(self, transcript: Transcript | None = None, should_fail: bool = False) -> None:
        self._transcript = transcript
        self._should_fail = should_fail
        self.invocations = 0

    def transcribe(self, audio_path: Path, timeout: float | None = None) -> Transcript:
        self.invocations += 1
        if self._should_fail:
            raise RuntimeError("fallback boom")
        assert self._transcript is not None
        return self._transcript


class _FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        self.current += 0.1
        return self.current


class _FakeSRTSerializer:
    def __init__(self) -> None:
        self.invocations = 0

    def write(self, transcript: Transcript, audio_path: Path) -> Path:
        self.invocations += 1
        target = audio_path.with_suffix(".srt")
        target.write_text("srt", encoding="utf-8")
        return target


@pytest.fixture()
def base_transcript() -> Transcript:
    segment = Segment(sequence=1, speaker="Speaker 1", start=0.0, end=1.0, text="hello")
    metadata = TranscriptMetadata(
        total_duration=1.0,
        speaker_count=1,
        provenance=TranscriptProvenance.DIARIZATION,
    )
    return Transcript(segments=[segment], metadata=metadata)


def test_transcribe_success_uses_diarization(tmp_path: Path, base_transcript: Transcript) -> None:
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"")
    srt_file = audio_file.with_suffix(".srt")
    srt_file.write_text("dummy", encoding="utf-8")

    runner = _FakeRunner(_FakeRunResult(ok=True, srt_path=srt_file))
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback()
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=True)

    transcript = service.transcribe(audio_file, config)

    assert transcript.metadata.provenance is TranscriptProvenance.DIARIZATION
    assert transcript.metadata.speaker_count == 1
    assert runner.invocations == 1
    assert parser.invocations == 1
    assert fallback.invocations == 0
    assert srt_serializer.invocations == 0


def test_transcribe_uses_srt_when_returncode_nonzero(
    tmp_path: Path, base_transcript: Transcript, caplog: pytest.LogCaptureFixture
) -> None:
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"")
    srt_file = audio_file.with_suffix(".srt")
    srt_file.write_text("dummy", encoding="utf-8")

    runner = _FakeRunner(
        _FakeRunResult(ok=False, srt_path=srt_file, returncode=1)
    )
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback()
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=True)

    with caplog.at_level(logging.WARNING):
        transcript = service.transcribe(audio_file, config)

    assert transcript.metadata.provenance is TranscriptProvenance.DIARIZATION
    assert fallback.invocations == 0
    assert srt_serializer.invocations == 0
    assert "reported failure but produced SRT" in caplog.text


def test_transcribe_runs_fallback_when_diarization_fails(tmp_path: Path, base_transcript: Transcript) -> None:
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"")

    runner = _FakeRunner(_FakeRunResult(ok=False, srt_path=None))
    fallback_transcript = Transcript(
        segments=base_transcript.segments,
        metadata=TranscriptMetadata(
            total_duration=5.0,
            speaker_count=0,
            provenance=TranscriptProvenance.FASTER_WHISPER,
        ),
    )
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback(transcript=fallback_transcript)
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=True)

    transcript = service.transcribe(audio_file, config)

    assert transcript.metadata.provenance is TranscriptProvenance.FASTER_WHISPER
    assert transcript.metadata.speaker_count == 0
    assert fallback.invocations == 1
    assert srt_serializer.invocations == 1
    assert (audio_file.with_suffix(".srt")).exists()


def test_transcribe_raises_when_audio_missing(tmp_path: Path, base_transcript: Transcript) -> None:
    runner = _FakeRunner(_FakeRunResult(ok=True, srt_path=None))
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback(transcript=base_transcript)
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=True)

    with pytest.raises(InvalidInputError):
        service.transcribe(tmp_path / "missing.wav", config)


def test_transcribe_raises_when_fallback_disabled(tmp_path: Path, base_transcript: Transcript) -> None:
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"")

    runner = _FakeRunner(_FakeRunResult(ok=False, srt_path=None, stdout="boom", stderr="oops", returncode=1))
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback(transcript=base_transcript)
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=False)

    with pytest.raises(DiarizationFailure) as exc_info:
        service.transcribe(audio_file, config)

    cause = exc_info.value.__cause__
    assert cause is not None
    assert getattr(cause, "returncode", None) == 1


def test_transcribe_raises_when_fallback_also_fails(
    tmp_path: Path, base_transcript: Transcript, caplog: pytest.LogCaptureFixture
) -> None:
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"")

    runner = _FakeRunner(_FakeRunResult(ok=False, srt_path=None))
    parser = _FakeParser(base_transcript)
    fallback = _FakeFallback(should_fail=True)
    srt_serializer = _FakeSRTSerializer()
    clock = _FakeClock()

    service = TranscriptionService(runner, parser, fallback, srt_serializer, clock)
    config = TranscriptionConfig(timeout_seconds=10, allow_fallback=True)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(DiarizationFailure):
            service.transcribe(audio_file, config)

    assert "Fallback transcription failed" in caplog.text

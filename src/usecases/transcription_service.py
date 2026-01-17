from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from src.domain.errors import (
    DiarizationFailure,
    DiarizationProcessError,
    InvalidInputError,
)
from src.domain.models import Transcript, TranscriptMetadata, TranscriptProvenance
from src.usecases.ports import (
    Clock,
    DiarizationRunResult,
    DiarizationRunner,
    FallbackTranscriber,
    TranscriptParser,
    TranscriptSRTSerializer,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptionConfig:
    timeout_seconds: float
    allow_fallback: bool = True


class TranscriptionService:
    def __init__(
        self,
        diarization_runner: DiarizationRunner,
        transcript_parser: TranscriptParser,
        fallback_transcriber: FallbackTranscriber,
        srt_serializer: TranscriptSRTSerializer,
        clock: Clock,
    ) -> None:
        self._runner = diarization_runner
        self._parser = transcript_parser
        self._fallback = fallback_transcriber
        self._srt_serializer = srt_serializer
        self._clock = clock

    def transcribe(self, audio_path: Path, config: TranscriptionConfig) -> Transcript:
        if not audio_path.exists() or not audio_path.is_file():
            raise InvalidInputError(f"Audio file not found: {audio_path}")

        logger.info("Starting diarization pipeline", extra={"audio_path": str(audio_path)})
        run_result = self._runner.run(audio_path, timeout=config.timeout_seconds)

        srt_path = run_result.srt_path
        if srt_path and srt_path.exists():
            if run_result.ok:
                logger.info(
                    "Diarization pipeline succeeded", extra={"audio_path": str(audio_path)}
                )
            else:
                logger.warning(
                    "Diarization subprocess reported failure but produced SRT",
                    extra={
                        "audio_path": str(audio_path),
                        "returncode": getattr(run_result, "returncode", None),
                    },
                )

            transcript = self._parser.parse(srt_path)
            metadata = TranscriptMetadata(
                total_duration=transcript.metadata.total_duration,
                speaker_count=transcript.metadata.speaker_count,
                provenance=TranscriptProvenance.DIARIZATION,
            )
            return Transcript(segments=transcript.segments, metadata=metadata)

        logger.warning(
            "Diarization pipeline failed, evaluating fallback",
            extra={
                "audio_path": str(audio_path),
                "returncode": getattr(run_result, "returncode", None),
            },
        )

        if not config.allow_fallback:
            self._raise_failure(run_result)

        fallback_start = self._clock.monotonic()
        try:
            transcript = self._fallback.transcribe(
                audio_path, timeout=config.timeout_seconds
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Fallback transcription failed",
                extra={"audio_path": str(audio_path)},
            )
            raise DiarizationFailure("diarization failed") from exc

        elapsed = self._clock.monotonic() - fallback_start
        logger.info(
            "Fallback transcription succeeded",
            extra={"audio_path": str(audio_path), "elapsed_seconds": elapsed},
        )

        try:
            self._srt_serializer.write(transcript, audio_path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to persist fallback SRT",
                extra={"audio_path": str(audio_path)},
            )
            raise DiarizationFailure("diarization failed") from exc

        metadata = TranscriptMetadata(
            total_duration=transcript.metadata.total_duration,
            speaker_count=0,
            provenance=TranscriptProvenance.FASTER_WHISPER,
        )
        return Transcript(segments=transcript.segments, metadata=metadata)

    @staticmethod
    def _raise_failure(run_result: DiarizationRunResult) -> None:
        error = DiarizationProcessError(
            message="Diarization subprocess failed",
            stdout=getattr(run_result, "stdout", ""),
            stderr=getattr(run_result, "stderr", ""),
            returncode=getattr(run_result, "returncode", 0),
        )
        raise DiarizationFailure("diarization failed") from error


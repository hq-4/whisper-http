from __future__ import annotations

from src.adapters.diarization_runner import DiarizationSubprocessRunner
from src.adapters.fallback_transcriber import FasterWhisperFallbackTranscriber
from src.adapters.json_serializer import TranscriptJSONSerializer
from src.adapters.srt_serializer import TranscriptSRTSerializer
from src.adapters.srt_parser import SRTTranscriptParser
from src.adapters.time_provider import SystemClock
from src.framework.config import Settings
from src.usecases.transcription_service import TranscriptionConfig, TranscriptionService


class Container:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._clock = SystemClock()
        self._parser = SRTTranscriptParser()
        self._runner = DiarizationSubprocessRunner(settings.diarization_repo_path)
        self._fallback = FasterWhisperFallbackTranscriber(
            model_name=settings.model_size,
            language=settings.fallback_language,
        )
        self._serializer = TranscriptJSONSerializer()
        self._srt_serializer = TranscriptSRTSerializer()
        self._service = TranscriptionService(
            diarization_runner=self._runner,
            transcript_parser=self._parser,
            fallback_transcriber=self._fallback,
            srt_serializer=self._srt_serializer,
            clock=self._clock,
        )

    @property
    def transcription_service(self) -> TranscriptionService:
        return self._service

    @property
    def serializer(self) -> TranscriptJSONSerializer:
        return self._serializer

    @property
    def srt_serializer(self) -> TranscriptSRTSerializer:
        return self._srt_serializer

    @property
    def settings(self) -> Settings:
        return self._settings

    def build_config(self) -> TranscriptionConfig:
        return TranscriptionConfig(
            timeout_seconds=self._settings.request_timeout_seconds,
            allow_fallback=self._settings.fallback_enabled,
        )

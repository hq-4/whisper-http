from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import srt

from src.domain.models import Transcript, TranscriptProvenance


MAX_SEGMENT_DURATION_SECONDS = 30.0


class TranscriptSRTSerializer:
    def write(self, transcript: Transcript, audio_path: Path) -> Path:
        target_path = audio_path.with_suffix(".srt")
        subtitles = self._build_subtitles(transcript)
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

    def _build_subtitles(self, transcript: Transcript) -> list[srt.Subtitle]:
        cleaned_segments = self._prepare_segments(transcript)
        subtitles: list[srt.Subtitle] = []
        for sequence, entry in enumerate(cleaned_segments, start=1):
            text = entry["text"]
            speaker = entry["speaker"]
            if speaker:
                text = f"{speaker}: {text}"

            start_seconds = entry["start"]
            end_seconds = entry["end"]
            subtitles.append(
                srt.Subtitle(
                    index=sequence,
                    start=timedelta(seconds=start_seconds),
                    end=timedelta(seconds=end_seconds),
                    content=text,
                )
            )
        return subtitles

    def _prepare_segments(self, transcript: Transcript) -> list[dict[str, float | str | None]]:
        prepared: list[dict[str, float | str | None]] = []
        provenance = transcript.metadata.provenance
        for segment in transcript.segments:
            text = segment.text.strip()
            if not text:
                continue

            normalized_text = self._normalize_text(text)
            start_seconds = max(float(segment.start), 0.0)
            end_seconds = max(float(segment.end), start_seconds)
            if end_seconds <= start_seconds:
                end_seconds = start_seconds + 0.01

            speaker_raw = segment.speaker.strip() if segment.speaker else ""
            if provenance is TranscriptProvenance.FASTER_WHISPER and speaker_raw == "Speaker 0":
                speaker_raw = ""
            speaker_value = speaker_raw or None

            if prepared:
                previous = prepared[-1]
                if (
                    previous["speaker"] == speaker_value
                    and previous["normalized_text"] == normalized_text
                ):
                    previous["text"] = previous["text"] or text
                    if end_seconds - previous["start"] <= MAX_SEGMENT_DURATION_SECONDS:
                        previous["end"] = max(previous["end"], end_seconds)
                        continue

            prepared.append(
                {
                    "speaker": speaker_value,
                    "text": text,
                    "normalized_text": normalized_text,
                    "start": start_seconds,
                    "end": end_seconds,
                }
            )

        expanded: list[dict[str, float | str | None]] = []
        for entry in prepared:
            normalized = entry.pop("normalized_text", None)
            duration = entry["end"] - entry["start"]
            if duration > MAX_SEGMENT_DURATION_SECONDS and normalized is not None:
                expanded.extend(
                    self._split_entry(entry, normalized, MAX_SEGMENT_DURATION_SECONDS)
                )
            else:
                expanded.append(entry)
        return expanded

    def _split_entry(
        self,
        entry: dict[str, float | str | None],
        normalized_text: str,
        max_duration: float,
    ) -> list[dict[str, float | str | None]]:
        start = entry["start"]
        end = entry["end"]
        text = entry["text"]
        speaker = entry.get("speaker")
        pieces: list[dict[str, float | str | None]] = []
        while start < end:
            slice_end = min(start + max_duration, end)
            pieces.append(
                {
                    "speaker": speaker,
                    "text": text,
                    "start": start,
                    "end": slice_end,
                }
            )
            start = slice_end
        return pieces

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split()).casefold()

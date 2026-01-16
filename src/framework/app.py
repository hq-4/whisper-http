from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request
from pydantic import BaseModel, ValidationError

from src.domain.errors import DiarizationFailure, InvalidInputError, TranscriptError
from src.domain.models import TranscriptProvenance
from src.framework.config import load_settings
from src.framework.container import Container
from src.framework.logging_config import configure_logging

logger = logging.getLogger(__name__)


class TranscriptionPayload(BaseModel):
    audio_path: Path


def create_app() -> Flask:
    settings = load_settings()
    configure_logging(settings)
    container = Container(settings)

    app = Flask(__name__)
    app.config["container"] = container

    @app.route("/transcribe", methods=["POST"])
    def transcribe() -> Any:
        payload = _parse_payload()
        container: Container = app.config["container"]
        service = container.transcription_service
        config = container.build_config()
        serializer = container.serializer
        srt_serializer = container.srt_serializer

        try:
            transcript = service.transcribe(payload.audio_path, config)
        except InvalidInputError as exc:
            logger.warning("Invalid transcription request", exc_info=exc)
            return jsonify({"error": exc.message}), 400
        except DiarizationFailure as exc:
            _log_failure(exc)
            return jsonify({"type": "diarization", "message": "diarization failed"}), 500
        except TranscriptError as exc:
            logger.exception("Transcript error", exc_info=exc)
            return jsonify({"error": exc.message}), 500
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error during transcription")
            return jsonify({"error": "internal server error"}), 500

        srt_path = payload.audio_path.with_suffix(".srt")
        if (
            transcript.metadata.provenance is TranscriptProvenance.FASTER_WHISPER
            or not srt_path.exists()
        ):
            srt_serializer.write(transcript, payload.audio_path)

        serializer.write(transcript, payload.audio_path)
        response = serializer.to_dict(transcript)
        response["json_path"] = str(payload.audio_path.with_suffix(".json"))
        response["srt_path"] = str(payload.audio_path.with_suffix(".srt"))
        return jsonify(response), 200

    return app


def _parse_payload() -> TranscriptionPayload:
    try:
        data: Dict[str, Any] = request.get_json(force=True, silent=False)  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover - flask wraps bad json as BadRequest
        raise InvalidInputError("Invalid JSON payload") from exc

    try:
        payload = TranscriptionPayload.model_validate(data)
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc

    return payload


def _log_failure(exc: DiarizationFailure) -> None:
    logger.error("Diarization pipeline failed after fallback", exc_info=exc)
    cause = exc.__cause__
    if isinstance(cause, TranscriptError):
        logger.error(
            "Diarization failure details",
            extra={
                "stdout": getattr(cause, "stdout", ""),
                "stderr": getattr(cause, "stderr", ""),
                "returncode": getattr(cause, "returncode", None),
            },
        )


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=8000, threaded=False)

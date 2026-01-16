from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.framework.app import create_app


@pytest.mark.integration
def test_transcribe_endpoint_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_audio = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "audio" / "hq2min.mp3"
    audio_path = tmp_path / fixture_audio.name
    shutil.copyfile(fixture_audio, audio_path)

    monkeypatch.delenv("LANGUAGE", raising=False)
    monkeypatch.delenv("MODEL_SIZE", raising=False)
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "600")

    app = create_app()

    with app.test_client() as client:
        response = client.post(
            "/transcribe",
            data=json.dumps({"audio_path": str(audio_path)}),
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["provenance"] in {"diarization", "faster_whisper"}
    if payload["provenance"] == "diarization":
        assert payload["speaker_count"] >= 1
    else:
        assert payload["speaker_count"] == 0
    assert len(payload["segments"]) >= 1
    assert "srt_path" in payload

    json_output = audio_path.with_suffix(".json")
    srt_output = audio_path.with_suffix(".srt")
    assert json_output.exists()
    assert srt_output.exists()
    saved_payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert saved_payload["provenance"] == payload["provenance"]
    assert len(saved_payload["segments"]) == len(payload["segments"])

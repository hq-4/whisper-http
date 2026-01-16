# whisper-http

Single-client Flask service that orchestrates Whisper diarization via a git submodule and falls back to faster-whisper when diarization fails. Responses are returned as JSON with segment metadata and provenance, and a `.json` artifact is saved alongside the source audio.

## Prerequisites

- Python 3.11 (managed via [`uv`](https://github.com/astral-sh/uv))
- Git submodules enabled
- NVIDIA GPU optional (auto-detected by faster-whisper)
- Optional: Hugging Face token (`HF_TOKEN`) for faster model downloads

## Initial Setup

```bash
# Clone the repo and initialize submodule (pinned commit recorded in .gitmodules)
git clone <repo>
cd whisper-http
git submodule update --init --recursive

# Create isolated environment and install dependencies via uv
uv venv
uv sync
# Install diarization submodule requirements (includes pinned torch/Nemo stack)
./utils/bootstrap_diarization.sh

# (Optional) warm Hugging Face cache for faster-whisper
uv run python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("large-v3", device="auto")
PY
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed:

```
LANGUAGE=turbo           # only 'turbo' currently allowed (auto-detect)
MODEL_SIZE=large-v3      # allowed values: turbo, large-v3
REQUEST_TIMEOUT_SECONDS=600
FALLBACK_ENABLED=true
LOG_LEVEL=INFO
```

Derived settings:

- Logs written to `logs/app.jsonl` (auto-created, rotated at 10 MB x5).
- Diarization submodule expected at `external/whisper-diarization`.

## Running the Service

```bash
uv run python src/framework/app.py
# Service listens on http://0.0.0.0:8000 (single-threaded).
```

### Request Schema

```
POST /transcribe
Content-Type: application/json

{
  "audio_path": "/absolute/path/to/audio.wav"
}
```

### Response Schema

On success:

```json
{
  "provenance": "diarization",
  "total_duration": 123.45,
  "speaker_count": 2,
  "segments": [
    {
      "sequence": 1,
      "speaker": "Speaker 1",
      "start": 0.0,
      "end": 5.2,
      "text": "..."
    }
  ],
  "json_path": "/absolute/path/to/audio.json"
}
```

If diarization and fallback both fail:

```json
{
  "type": "diarization",
  "message": "diarization failed"
}
```

Logs include subprocess stdout/stderr, Rich-formatted console output, and JSONL structured records.

## Testing

- Run entire suite (unit + integration):

  ```bash
  uv run -m pytest -q
  ```

- Run only unit tests:

  ```bash
  uv run -m pytest -q -m "not integration"
  ```

Audio fixtures reside in `tests/fixtures/audio/` (~2 minutes each). Expect the first integration run to download models.

## Linting & Formatting

```bash
uv run ruff check .
uv run ruff format .
```

## Updating the Diarization Submodule

- Pinned commit recorded in `.gitmodules`.
- To update:
  1. `git submodule update --remote external/whisper-diarization`
  2. Verify compatibility and note the new commit hash.
  3. Re-run the full test suite (`uv run -m pytest -q`).

## Manual Sanity Check

1. Place target audio on disk accessible to the server.
2. Run the app: `uv run python src/framework/app.py`
3. Submit request:

   ```bash
   curl -X POST http://localhost:8000/transcribe \
     -H 'Content-Type: application/json' \
     -d '{"audio_path": "/path/audio.mp3"}'
   ```

4. Inspect response JSON and the generated `<audio>.json` and `<audio>.srt` files for provenance and segment details.

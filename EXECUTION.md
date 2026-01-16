# Execution Plan

## Overview
Implement a single-threaded Flask service that orchestrates diarization and fallback transcription using a git-submodule-sourced pipeline while adhering to UV-managed environments, dual-sink logging, and defined JSON schema/output semantics.

## Key Components

1. **Repository Setup & Dependencies**
   - Add `whisper-diarization` as git submodule pinned to documented commit (`.gitmodules`).
   - Ensure UV installs both project deps and submodule requirements (`uv pip install -c constraints.txt -r requirements.txt`).
   - Define `.env.example` with language (`turbo`), model size (`large-v3`), timeout (≤600s), and GPU toggle settings.

2. **Application Structure (Clean Architecture)**
   - **Domain**: Define transcript entities (segments, metadata), error enums, and value objects (speaker labels, timestamps in float seconds).
   - **Usecases**: Implement orchestration service to run diarization subprocess, detect failures, trigger faster-whisper fallback, and consolidate outputs.
   - **Adapters**: 
     - Subprocess adapter invoking `python diarize.py -a <audio_path>` inside submodule path.
     - Fallback faster-whisper adapter (likely Python invocation using installed package) respecting model config and JSON artifact creation.
     - File I/O for JSON write/read.
   - **Framework**: Flask app, dependency injection wiring, config loading, logging bootstrap enforcing dual handlers.

3. **Process Flow**
   1. Receive `POST /transcribe` with `{ "audio_path": "..." }`.
   2. Validate path existence and readability; ensure response timeout configuration (default 600s from `.env`).
   3. Launch diarization subprocess via `subprocess.run` (with `check=False`), capturing stdout/stderr; enforce timeout.
   4. On success: locate generated `.srt`, parse to JSON (segments with sequence numbers, start/end float seconds, speaker field, text). Compute metadata: total duration (seconds), speaker count, provenance `"diarization"`.
   5. On failure: log stderr/stdout with Rich tracebacks, set provenance `"faster_whisper"`, run fallback adapter producing equivalent JSON. If fallback also fails, return `{ "type": "diarization", "message": "diarization failed" }` with HTTP 500.
   6. Return JSON payload directly; optionally persist `.json` file adjacent to audio (if requirement emerges).

4. **JSON Schema**
   ```json
   {
     "provenance": "diarization",
     "total_duration": 1234.56,
     "speaker_count": 3,
     "segments": [
       {
         "sequence": 1,
         "speaker": "Speaker 2",
         "start": 0.0,
         "end": 5.432,
         "text": "Hello world"
       }
     ]
   }
   ```
   - `start/end` in float seconds.
   - `speaker_count` == 0 if diarization failed and fallback succeeded.

5. **Logging & Monitoring**
   - Initialize logging enforcer verifying Rich console + JSONL handlers (`logs/app.jsonl`).
   - On subprocess failure, log stderr/stdout plus exception info with stack trace.
   - Include request/response summary at INFO level (sanitized).

6. **Timeout & Configuration**
   - Load `.env` via framework config module.
   - Enforce request-level timeout ≤ configured limit (guarding subprocess and fallback).
   - Validate language/model values against whitelist {`turbo`, `large-v3`}.

7. **Testing Strategy**
   - **Unit Tests**: JSON parsing, schema validation, error handling, config validation, fallback decision logic.
   - **Integration Tests (default)**: Use curated fixtures (2 min pass sample, 2 min fail sample) stored in `tests/fixtures/audio/`. Run diarization end-to-end via real subprocess; ensure runtime ≤10 minutes.
   - Mock fallback failure to validate error response.

8. **Documentation Updates**
   - README: setup (UV sync, submodule init, `uv pip install -c constraints.txt -r requirements.txt`), `.env` instructions, running server (`uv run python src/framework/app.py`), testing commands.
   - `IMPLEMENTATION_PLAN.md`: reference for submodule hash updates process.

9. **Future Considerations**
   - Potential caching of JSON results per audio hash.
   - Async job queue if concurrency needs evolve.

## Execution Sequencing
1. ✅ Bootstrap repo (submodule pinned, UV env + submodule deps installed, directory scaffolding & `.env.example` seeded).
2. ✅ Implement domain/usecase layers and adapters incrementally (domain models, error types, transcription service, diarization runner, faster-whisper fallback, clock, and SRT parser ready).
3. ✅ Build Flask endpoint with logging, validation, and orchestration wiring (config loader, logging bootstrap, DI container, and /transcribe route implemented).
4. ✅ Develop SRT→JSON conversion parser respecting metadata rules (SRT parser + JSON serializer integrated into transcription flow).
5. ✅ Add fallback integration and error propagation (subprocess runner handles timeouts, Flask error mapping complete, unit tests covering failure paths pending execution).
6. ✅ Write robust unit + integration tests; incorporated 2-minute fixtures, expanded failure-case coverage (service + parser + serializer + HTTP integration), and asserted logging behavior.
7. Update docs, verify lint/tests (`uv run ruff check .`, `uv run -m pytest -q`).
8. Manual sanity run with provided sample audio paths to confirm end-to-end flow.

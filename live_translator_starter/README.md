# Live Translator Starter

Starter project for a low-latency speech translation app.

The first version intentionally uses fake ASR, fake translation, and browser-side speech synthesis so you can verify the WebRTC/audio/UI plumbing before adding heavy models.

## Runtime flow

```text
Browser microphone
  -> WebRTC audio track
  -> FastAPI + aiortc backend
  -> ASR module
  -> stable text buffer
  -> translation module
  -> TTS/voice module
  -> UI events + placeholder browser TTS
```

## Quick start

```bash
cd live_translator_starter
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn server.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```

Click **Start session**, allow microphone access, and speak. The server receives real microphone audio over WebRTC, but the ASR/translation output is simulated until you replace the pipeline modules.

## Where to swap real models

- `server/app/pipeline/asr.py`: replace `FakeASR` with Whisper, Parakeet, NeMo/Riva, etc.
- `server/app/pipeline/translator.py`: replace `FakeTranslator` with Hy-MT2, CAT-Translate, Qwen, LMT-60, etc.
- `server/app/pipeline/tts.py`: replace browser placeholder with server-side TTS.
- `server/app/pipeline/voice_selector.py`: add masculine/feminine/neutral and low/medium/high pitch matching.
- `server/app/pipeline/stable_buffer.py`: tune when ASR text is safe to translate/speak.

## Optional local LLM translator example

See `server/app/examples/hf_llm_translator.py` for a Transformers-based translator wrapper. That file is not imported by default so the basic server stays lightweight.

## Production note

This starter uses one FastAPI process for simplicity. For production, split WebRTC gateway, ASR, translation, TTS, session state, and metrics into separate services.

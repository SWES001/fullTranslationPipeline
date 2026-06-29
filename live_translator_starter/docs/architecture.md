# Architecture

```text
Client browser
  -> getUserMedia microphone capture
  -> RTCPeerConnection WebRTC audio track using Opus
  -> Python backend with aiortc
  -> audio frame consumer
  -> ASR module
  -> stable text buffer
  -> translation module
  -> TTS + voice selector
  -> translated speech/audio output
```

## MVP boundaries

Keep these modules separate even if they run in one process:

- WebRTC gateway
- ASR
- stable text buffer
- translation
- TTS
- voice selection
- metrics

## Why the stable text buffer exists

Streaming ASR changes its mind. Captions can be revised, but already-spoken TTS audio cannot. The stable buffer prevents unstable ASR text from being translated and spoken too early.

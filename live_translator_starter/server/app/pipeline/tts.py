from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_bytes: bytes
    content_type: str
    voice_id: str


class FakeTTS:
    """Placeholder for server-side TTS.

    The browser UI currently uses Web Speech API as a temporary TTS layer.
    Replace this class with Riva, CosyVoice, Kokoro, ElevenLabs, or another
    streaming TTS engine when you are ready to return audio from the server.
    """

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        return TTSResult(audio_bytes=b"", content_type="audio/wav", voice_id=voice_id)

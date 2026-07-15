from dataclasses import dataclass, field
from typing import Iterable, Optional
from uuid import uuid4

from server.app.pipeline.asr import FakeASR, QwenASR, FastWhisperASR, CohereASR
from server.app.pipeline.stable_buffer import StableTextBuffer
from server.app.pipeline.translator import FakeTranslator, HyMT2Translator
from server.app.pipeline.voice_selector import VoiceSelector


@dataclass
class TranslationSession:
    source_language: str
    target_language: str
    model_name: str
    asr_model: str = "fake"
    voice_matching: bool = False
    session_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if self.asr_model == "openai/whisper-large-v3":
            self.asr = FastWhisperASR(server_ip="74.2.96.26")
        elif self.asr_model == "Qwen/Qwen3-ASR-1.7B":
            self.asr = QwenASR(server_ip="74.2.96.26")
        elif self.asr_model == "CohereLabs/cohere-transcribe-03-2026":
            self.asr = CohereASR(server_ip="74.2.96.26")
        else:
            self.asr = FakeASR()
            
        if self.model_name == "tencent/Hy-MT2-1.8B":
            self.translator = HyMT2Translator()
        else:
            self.translator = FakeTranslator(model_name=self.model_name)
        self.stable_buffer = StableTextBuffer()
        self.voice_selector = VoiceSelector()

    async def process_audio_window(self, frames: Iterable[object]) -> Optional[dict]:
        asr_result = await self.asr.transcribe_pcm(frames, self.source_language)
        committed_text = self.stable_buffer.commit(asr_result)

        if not committed_text:
            return {
                "type": "asr_partial",
                "session_id": self.session_id,
                "source": {
                    "text": asr_result.text,
                    "language": asr_result.language,
                    "confidence": asr_result.confidence,
                },
            }

        translated_text = await self.translator.translate(
            committed_text,
            source_language=self.source_language,
            target_language=self.target_language,
        )
        voice = self.voice_selector.select(self.target_language, self.voice_matching)

        return {
            "type": "translation",
            "session_id": self.session_id,
            "source": {
                "text": committed_text,
                "language": self.source_language,
                "confidence": asr_result.confidence,
            },
            "translation": {
                "text": translated_text,
                "language": self.target_language,
                "model": self.model_name,
            },
            "voice": {
                "voice_id": voice.voice_id,
                "presentation": voice.presentation,
                "pitch_bucket": voice.pitch_bucket,
            },
        }

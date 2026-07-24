from dataclasses import dataclass, field
from typing import Iterable, Optional
from uuid import uuid4

from server.app.config import config
from server.app.pipeline.asr import FakeASR, QwenASR, FastWhisperASR, CohereASR, ByteComputeGemmaASR, ByteComputeWhisperASR
from server.app.pipeline.stable_buffer import StableTextBuffer
from server.app.pipeline.translator import FakeTranslator, HyMT2Translator, ByteComputeTranslator
from server.app.pipeline.voice_selector import VoiceSelector
from server.app.pipeline.tts import FakeTTS, MossTTS, HiggsAudioTTS, Qwen3TTS, HiggsTTSv3, ByteComputeHiggsSpeechV3, KokoroServerTTS


@dataclass
class TranslationSession:
    source_language: str
    target_language: str
    model_name: str
    asr_model: str = "fake"
    tts_model: str = "Kokoro-82M-Server"
    voice_matching: bool = False
    session_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if self.asr_model in ("bytecompute/gemma-4-E4B-it", "google/gemma-4-E4B-it", "gemma-4-E4B-it", "gemma-4-e4b"):
            self.asr = ByteComputeGemmaASR()
        elif self.asr_model in ("openai/whisper-large-v3", "whisper-large-v3", "bytecompute/whisper-large-v3"):
            self.asr = ByteComputeWhisperASR()
        # elif self.asr_model == "Qwen/Qwen3-ASR-1.7B":
        #     self.asr = QwenASR(server_ip=config.asr_server_ip)
        elif self.asr_model == "CohereLabs/cohere-transcribe-03-2026":
            self.asr = CohereASR(server_ip=config.asr_server_ip)
        else:
            self.asr = FakeASR()
            
        if self.model_name == "tencent/Hy-MT2-1.8B":
            self.translator = HyMT2Translator(server_ip=config.translator_server_ip)
        elif self.model_name in ("bytecompute/gemma-4-E4B-it", "google/gemma-4-E4B-it"):
            self.translator = ByteComputeTranslator()
        else:
            self.translator = FakeTranslator(model_name=self.model_name)

        if self.tts_model in ("Kokoro-82M-Server", "Kokoro-82M", "kokoro-server", "kokoro"):
            self.tts = KokoroServerTTS(server_ip=config.tts_server_ip, port=31241)
        elif self.tts_model in ("bytecompute/higgs-speech-v3", "higgs-speech-v3"):
            self.tts = ByteComputeHiggsSpeechV3()
        elif self.tts_model in ("Higgs-TTS-v3", "higgs-tts-v3"):
            self.tts = HiggsTTSv3(server_ip=config.tts_server_ip, port=31250)
        elif self.tts_model == "Moss-TTS-v1.5":
            self.tts = MossTTS(server_ip=config.tts_server_ip, port=31240)
        # elif self.tts_model == "Qwen3-TTS-1.7B":
        #     self.tts = Qwen3TTS(server_ip=config.tts_server_ip, port=31411)
        elif self.tts_model in ("boson/higgs-audio-v2.5", "boson-audio-multimodal-checkpoint-1200"):
            self.tts = HiggsAudioTTS()
        else:
            self.tts = FakeTTS()

        self.stable_buffer = StableTextBuffer()
        self.voice_selector = VoiceSelector()

    async def process_audio_window(self, frames: Iterable[object]) -> Optional[dict]:
        import time
        start_time = time.time()

        asr_result = await self.asr.transcribe_pcm(frames, self.source_language)
        asr_end = time.time()
        asr_ms = int((asr_end - start_time) * 1000)

        committed_text = self.stable_buffer.commit(asr_result)

        if not committed_text:
            return {
                "type": "asr_partial",
                "session_id": self.session_id,
                "asr_ms": asr_ms,
                "source": {
                    "text": asr_result.text,
                    "language": asr_result.language,
                    "confidence": asr_result.confidence,
                },
            }

        trans_start = time.time()
        translated_text = await self.translator.translate(
            committed_text,
            source_language=self.source_language,
            target_language=self.target_language,
        )
        trans_end = time.time()
        trans_ms = int((trans_end - trans_start) * 1000)
        ttft_ms = int((trans_end - start_time) * 1000)

        voice = self.voice_selector.select(self.target_language, self.voice_matching)

        tts_start = time.time()
        tts_result = await self.tts.synthesize(translated_text, voice.voice_id)
        tts_end = time.time()
        tts_ms = int((tts_end - tts_start) * 1000)
        ttfa_ms = int((tts_end - start_time) * 1000)
        
        import base64
        audio_base64 = base64.b64encode(tts_result.audio_bytes).decode("utf-8") if tts_result.audio_bytes else ""

        return {
            "type": "translation",
            "session_id": self.session_id,
            "asr_ms": asr_ms,
            "trans_ms": trans_ms,
            "tts_ms": tts_ms,
            "ttft_ms": ttft_ms,
            "ttfa_ms": ttfa_ms,
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
            "audio": {
                "data": audio_base64,
                "content_type": tts_result.content_type,
                "error": tts_result.error if hasattr(tts_result, "error") else "",
            }
        }

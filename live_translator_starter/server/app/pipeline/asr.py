import io
import wave
import httpx
import av
from dataclasses import dataclass, field
from itertools import cycle
from typing import Iterable, Protocol

@dataclass
class ASRResult:
    text: str
    is_final: bool
    confidence: float
    language: str

class ASR(Protocol):
    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        ...

def frames_to_wav_bytes(frames: list) -> bytes:
    """Helper to convert raw WebRTC audio frames into a 16kHz mono WAV file in memory."""
    if not frames:
        return b""
    
    wav_io = io.BytesIO()
    
    # 16kHz, mono (1 channel), 16-bit PCM is standard for speech recognition models
    sample_rate = 16000
    channels = 1
    sample_width = 2
    
    resampler = av.AudioResampler(format='s16', layout='mono', rate=sample_rate)
    
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        for frame in frames:
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                wav_file.writeframes(r_frame.to_ndarray().tobytes())
                
        # Flush the resampler
        flushed_frames = resampler.resample(None)
        for r_frame in flushed_frames:
            wav_file.writeframes(r_frame.to_ndarray().tobytes())
            
    return wav_io.getvalue()


@dataclass
class FakeASR:
    """Fake ASR used to test the app before adding a real speech model."""

    _ja_samples: object = field(default_factory=lambda: cycle([
        "えっと、明日の会議を午後三時に変更できますか？",
        "すみません、もう一回ゆっくり言ってもらえますか？",
        "この資料は今日中に確認します。",
    ]))
    _en_samples: object = field(default_factory=lambda: cycle([
        "Actually, can we move the meeting to next Wednesday instead?",
        "Could you please say that one more time slowly?",
        "I will review this document by the end of today.",
    ]))

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        text = next(self._ja_samples if source_language == "ja" else self._en_samples)
        return ASRResult(
            text=text,
            is_final=True,
            confidence=0.99,
            language=source_language,
        )


class QwenASR:
    """Connects to your company's Qwen3 vLLM ASR server (UNWIRED / DISABLED)."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 30407):
        # UNWIRED: Qwen3 disabled per requirement
        # self.url = f"http://{server_ip}:{port}/v1/audio/transcriptions"
        self.url = ""
        self.model_name = "Qwen/Qwen3-ASR-1.7B"
        self.api_key = "sk-proj-8-W-hNfM9cJ_t_gL4pQ4k_t2sXzY9uW9O0iZ7bA"

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        wav_bytes = frames_to_wav_bytes(list(frames))
        if not wav_bytes:
            return ASRResult(text="", is_final=True, confidence=0.0, language=source_language)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav")
            }
            
            # Language lock prompts to prevent the model from hallucinating other languages
            prompt_map = {
                "en": "English speech transcription.",
                "ja": "日本語の文字起こし。",
                "es": "Transcripción de voz en español.",
                "zh": "中文语音识别。"
            }
            prompt_text = prompt_map.get(source_language, "")
            
            data = {
                "model": self.model_name,
                "language": source_language,
            }
            if prompt_text:
                data["prompt"] = prompt_text
                
            try:
                response = await client.post(self.url, headers=headers, files=files, data=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                text = result.get("text", "")
                print(f"Qwen3 ASR Transcribed: '{text}'")
                return ASRResult(
                    text=text,
                    is_final=True,
                    confidence=0.99,
                    language=source_language,
                )
            except Exception as e:
                import traceback
                print(f"Qwen ASR Exception Traceback ({self.url}):")
                traceback.print_exc()
                return ASRResult(
                    text=f"[ASR Connection Error ({self.url}): {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language,
                )


WHISPER_HALLUCINATION_PHRASES = {
    "gracias", "gracias.", "gracias!", "¡gracias!", "gracias por ver", "gracias por ver.",
    "suscríbete", "suscríbete.", "suscríbete!", "¡suscríbete!", "suscribete", "suscribete.",
    "subtítulos por...", "subtítulos por amara.org", "subtítulos realizados por la comunidad de amara.org",
    "subtítulos por la comunidad de amara.org", "gracias por ver este video.", "gracias por ver este vídeo.",
    "thank you for watching", "thank you for watching.", "thanks for watching", "thanks for watching.",
    "subscribe", "subscribe.", "subscribe to my channel", "subtitles by", "subtitles by amara.org",
    "ご視聴ありがとうございました", "ご視聴ありがとうございました。", "チャンネル登録", "チャンネル登録お願いします",
    "谢谢观看", "谢谢观看。", "订阅", "点赞", "关注"
}


def filter_whisper_hallucinations(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    normalized = cleaned.lower().rstrip(".!?,")
    if normalized in {p.lower().rstrip(".!?,") for p in WHISPER_HALLUCINATION_PHRASES}:
        print(f"[ASR Filter] Suppressed Whisper YouTube hallucination: '{cleaned}'")
        return ""
    for phrase in WHISPER_HALLUCINATION_PHRASES:
        p_norm = phrase.lower().rstrip(".!?,")
        if len(p_norm) > 5 and p_norm in normalized:
            if len(normalized) < len(p_norm) + 15:
                print(f"[ASR Filter] Suppressed hallucination phrase inside text: '{cleaned}'")
                return ""
    return cleaned


class FastWhisperASR:
    """Connects to ByteCompute's serverless Whisper Large V3 ASR endpoint."""

    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/audio/transcriptions"
        self.model_name = "openai/whisper-large-v3"
        self.api_key = api_key

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        wav_bytes = frames_to_wav_bytes(list(frames))
        if not wav_bytes:
            return ASRResult(text="", is_final=True, confidence=0.0, language=source_language)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav")
            }
            data = {
                "model": self.model_name,
                "language": source_language,
                "prompt": "Real-time speech conversation. Do not include video credits, channel subscriptions, or subtitle text.",
            }
            try:
                response = await client.post(self.url, headers=headers, files=files, data=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                raw_text = result.get("text", "").strip()
                text = filter_whisper_hallucinations(raw_text)
                print(f"Whisper Large V3 ASR Transcribed: '{text}' (raw: '{raw_text}')")
                return ASRResult(
                    text=text,
                    is_final=True,
                    confidence=0.99 if text else 0.0,
                    language=source_language,
                )
            except Exception as e:
                import traceback
                print(f"Whisper Large V3 ASR Connection Error: {e}")
                traceback.print_exc()
                return ASRResult(
                    text=f"[Whisper ASR Error: {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language,
                )


ByteComputeWhisperASR = FastWhisperASR


class ByteComputeWhisperTurboASR:
    """Connects to ByteCompute's serverless Whisper Large Turbo ASR endpoint."""

    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/audio/transcriptions"
        self.model_name = "openai/whisper-large-v3-turbo"
        self.api_key = api_key

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        wav_bytes = frames_to_wav_bytes(list(frames))
        if not wav_bytes:
            return ASRResult(text="", is_final=True, confidence=0.0, language=source_language)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav")
            }
            data = {
                "model": self.model_name,
                "language": source_language,
                "prompt": "Real-time speech conversation. Do not include video credits, channel subscriptions, or subtitle text.",
            }
            try:
                response = await client.post(self.url, headers=headers, files=files, data=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                raw_text = result.get("text", "").strip()
                text = filter_whisper_hallucinations(raw_text)
                print(f"Whisper Turbo ASR Transcribed: '{text}' (raw: '{raw_text}')")
                return ASRResult(
                    text=text,
                    is_final=True,
                    confidence=0.99 if text else 0.0,
                    language=source_language,
                )
            except Exception as e:
                import traceback
                print(f"Whisper Turbo ASR Connection Error: {e}")
                traceback.print_exc()
                return ASRResult(
                    text=f"[Whisper Turbo ASR Error: {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language,
                )


class CohereASR:
    """Connects to your company's Cohere vLLM ASR server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31234):
        self.url = f"http://{server_ip}:{port}/v1/audio/transcriptions"
        self.model_name = "CohereLabs/cohere-transcribe-03-2026"

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        wav_bytes = frames_to_wav_bytes(list(frames))
        if not wav_bytes:
            return ASRResult(text="", is_final=True, confidence=0.0, language=source_language)
            
        async with httpx.AsyncClient() as client:
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav")
            }
            # Language lock prompts to prevent the model from hallucinating other languages
            prompt_map = {
                "en": "English speech transcription.",
                "ja": "日本語の文字起こし。",
                "es": "Transcripción de voz en español.",
                "zh": "中文语音识别。"
            }
            prompt_text = prompt_map.get(source_language, "")
            
            data = {
                "model": self.model_name,
                "language": source_language,
            }
            if prompt_text:
                data["prompt"] = prompt_text
            try:
                response = await client.post(self.url, files=files, data=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                
                return ASRResult(
                    text=result.get("text", ""),
                    is_final=True,
                    confidence=0.99,
                    language=source_language,
                )
            except Exception as e:
                print(f"Cohere ASR Connection Error: {e}")
                return ASRResult(
                    text=f"[ASR Connection Error: {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language,
                )


class ByteComputeGemmaASR:
    """Connects to ByteCompute's serverless AI API for speech recognition."""

    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/chat/completions"
        self.model_name = "gemma-4-E4B-it"
        self.api_key = api_key

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        import base64

        wav_bytes = frames_to_wav_bytes(list(frames))
        if not wav_bytes:
            return ASRResult(text="", is_final=True, confidence=0.0, language=source_language)

        lang_names = {
            "en": "English",
            "ja": "Japanese",
            "es": "Spanish",
            "zh": "Mandarin Chinese"
        }
        lang_str = lang_names.get(source_language, "English")
        audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        prompt_text = (
            f"Transcribe the spoken audio accurately in {lang_str}. "
            "Only return the exact transcribed text, without intro, quotes, or markdown."
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.0
        }
        headers_json = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers_json, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                text = result["choices"][0]["message"]["content"].strip()
                print(f"Gemma 4 E4B ASR Transcribed: '{text}'")
                return ASRResult(
                    text=text,
                    is_final=True,
                    confidence=0.99,
                    language=source_language
                )
            except Exception as e:
                import traceback
                print(f"ByteCompute Gemma ASR Exception Traceback ({self.url}):")
                traceback.print_exc()
                return ASRResult(
                    text=f"[Gemma ASR Error: {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language
                )



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
    """Connects to your company's Qwen3 vLLM ASR server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 30407):
        self.url = f"http://{server_ip}:{port}/v1/audio/transcriptions"
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
            data = {
                "model": self.model_name,
                "language": source_language,
            }
            try:
                response = await client.post(self.url, headers=headers, files=files, data=data, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return ASRResult(
                    text=result.get("text", ""),
                    is_final=True,
                    confidence=0.99,
                    language=source_language,
                )
            except Exception as e:
                print(f"Qwen ASR Connection Error: {e}")
                return ASRResult(
                    text=f"[ASR Connection Error: {e}]",
                    is_final=True,
                    confidence=0.0,
                    language=source_language,
                )


class FastWhisperASR:
    """Connects to your company's FastWhisper ASR server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 30089):
        self.url = f"http://{server_ip}:{port}/v1/audio/transcriptions"
        self.model_name = "openai/whisper-large-v3"
        self.api_key = "sk-proj-r-J-aPaMncE_e_gL1pQ9k_t2sXzY19W8Otok6YX"

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
            }
            try:
                response = await client.post(self.url, headers=headers, files=files, data=data, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return ASRResult(
                    text=result.get("text", ""),
                    is_final=True,
                    confidence=0.99,
                    language=source_language,
                )
            except Exception as e:
                print(f"FastWhisper ASR Connection Error: {e}")
                return ASRResult(
                    text=f"[ASR Connection Error: {e}]",
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
            # Optional language hint prompt
            prompt_text = "English speech transcription." if source_language == "en" else "日本語の文字起こし。"
            
            data = {
                "model": self.model_name,
                "language": source_language,
                "prompt": prompt_text,
            }
            try:
                response = await client.post(self.url, files=files, data=data, timeout=10.0)
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


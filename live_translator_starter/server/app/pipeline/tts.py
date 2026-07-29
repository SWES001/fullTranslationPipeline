import httpx
from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_bytes: bytes
    content_type: str
    voice_id: str
    error: str = ""


class FakeTTS:
    """Placeholder for server-side TTS.

    The browser UI currently uses Web Speech API as a temporary TTS layer.
    """

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        return TTSResult(audio_bytes=b"", content_type="audio/wav", voice_id=voice_id)


class MossTTS:
    """Connects to MOSS-TTS v1.5 API running on port 31240 on your company server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31240):
        self.url = f"http://{server_ip}:{port}/tts"
        self.model_name = "moss-tts"

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        payload = {
            "text": text,
            "language": voice_id if voice_id else "en",
        }
        if CACHED_REF_AUDIO_B64:
            payload["reference_audio"] = CACHED_REF_AUDIO_B64
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=60.0)
                response.raise_for_status()
                print(f"Moss TTS Synthesized: {len(response.content)} bytes")
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                import traceback
                print(f"Moss TTS Connection Error ({self.url}): {e}")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Moss TTS connection error ({self.url}): {e}"
                )


class Qwen3TTS:
    """Connects to Qwen3-TTS-1.7B running on your company server (UNWIRED / DISABLED)."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31411):
        # UNWIRED: Qwen3 disabled per requirement
        # self.url = f"http://{server_ip}:{port}/v1/audio/speech"
        self.url = ""
        self.model_name = "/models/Qwen3-TTS-12Hz-1.7B-Base"

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        import base64
        import os
        
        audio_b64 = ""
        ref_path = "reference.wav"
        if os.path.exists(ref_path):
            with open(ref_path, "rb") as f:
                audio_b64 = "data:audio/wav;base64," + base64.b64encode(f.read()).decode("utf-8")
                
        payload = {
            "model": self.model_name,
            "input": text,
            "response_format": "wav"
        }
        if audio_b64:
            payload["task_type"] = "Base"
            payload["ref_audio"] = audio_b64
            payload["x_vector_only_mode"] = True
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=10.0)
                response.raise_for_status()
                print(f"Qwen3 TTS Synthesized: {len(response.content)} bytes")
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except httpx.HTTPStatusError as e:
                import traceback
                print(f"Qwen3 TTS Exception Traceback ({self.url}):")
                print(f"Response Body: {e.response.text}")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Qwen3 TTS HTTP {e.response.status_code}: {e.response.text}"
                )
            except Exception as e:
                import traceback
                print(f"Qwen3 TTS General Exception Traceback ({self.url}):")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Qwen3 TTS connection error ({self.url}): {e}"
                )


def get_cached_reference_audio(ref_path: str = "reference.wav", max_seconds: float = 6.0) -> str:
    """Pre-encodes and caches reference audio, trimming to max_seconds for fast synthesis."""
    import os
    import base64
    import wave
    import io

    if not os.path.exists(ref_path):
        return ""
    try:
        with wave.open(ref_path, "rb") as w:
            rate = w.getframerate()
            channels = w.getnchannels()
            width = w.getsampwidth()
            max_frames = int(max_seconds * rate)
            audio_frames = w.readframes(max_frames)
            
            out_io = io.BytesIO()
            with wave.open(out_io, "wb") as w_out:
                w_out.setnchannels(channels)
                w_out.setsampwidth(width)
                w_out.setframerate(rate)
                w_out.writeframes(audio_frames)
                
            return "data:audio/wav;base64," + base64.b64encode(out_io.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error caching reference audio: {e}")
        return ""


# Cached reference audio Data URI
CACHED_REF_AUDIO_B64 = get_cached_reference_audio("reference.wav", max_seconds=6.0)


class HiggsTTSv3:
    """Connects to Higgs-TTS-v3 running on port 31250 on your company server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31250):
        self.url = f"http://{server_ip}:{port}/v1/audio/speech"
        self.model_name = "bosonai/higgs-tts-3-4b"

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        payload = {
            "model": self.model_name,
            "input": text,
            "response_format": "wav"
        }
        if CACHED_REF_AUDIO_B64:
            payload["task_type"] = "Base"
            payload["ref_audio"] = CACHED_REF_AUDIO_B64
            payload["x_vector_only_mode"] = True

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=60.0)
                response.raise_for_status()
                print(f"Higgs-TTS-v3 Synthesized: {len(response.content)} bytes")
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except httpx.HTTPStatusError as e:
                import traceback
                print(f"Higgs-TTS-v3 Exception Traceback ({self.url}):")
                print(f"Response Body: {e.response.text}")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Higgs-TTS-v3 HTTP {e.response.status_code}: {e.response.text}"
                )
            except Exception as e:
                import traceback
                print(f"Higgs-TTS-v3 General Exception Traceback ({self.url}):")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Higgs-TTS-v3 connection error ({self.url}): {e}"
                )


class ByteComputeHiggsSpeechV3:
    """Connects to ByteCompute's Higgs Speech V3 (boson-audio-multimodal-checkpoint-1200) serverless API."""

    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/chat/completions"
        self.model_name = "boson-audio-multimodal-checkpoint-1200"
        self.api_key = api_key

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        import base64
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": text}
            ],
            "modalities": ["text", "audio"]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                audio_data_base64 = result["choices"][0]["message"]["audio"]["data"]
                audio_bytes = base64.b64decode(audio_data_base64)
                print(f"Higgs Speech V3 (ByteCompute API) Synthesized: {len(audio_bytes)} bytes")
                return TTSResult(
                    audio_bytes=audio_bytes,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                import traceback
                print(f"Higgs Speech V3 ByteCompute API Exception Traceback ({self.url}):")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Higgs Speech V3 ByteCompute API error ({self.url}): {e}"
                )


class KokoroServerTTS:
    """Connects to Kokoro-82M API running on port 31241 on your company server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31241):
        self.url_tts = f"http://{server_ip}:{port}/tts"
        self.url_v1 = f"http://{server_ip}:{port}/v1/audio/speech"
        self.model_name = "kokoro-82m"

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        valid_kokoro_voices = {
            "af_heart", "af_bella", "af_nicole", "af_sky",
            "am_adam", "am_michael", "bf_emma", "bf_isabella",
            "bm_george", "bm_fable", "ef_dora", "em_alex",
            "jf_alpha", "jm_kento", "zf_xiaobei", "zm_yunjian",
            "ff_siwis", "if_sara"
        }
        
        actual_voice = "af_heart"
        if voice_id in valid_kokoro_voices:
            actual_voice = voice_id
        elif voice_id.startswith("es"):
            actual_voice = "ef_dora"
        elif voice_id.startswith("ja"):
            actual_voice = "jf_alpha"
        elif voice_id.startswith("zh"):
            actual_voice = "zf_xiaobei"
        elif voice_id.startswith("fr"):
            actual_voice = "ff_siwis"
        elif voice_id.startswith("it"):
            actual_voice = "if_sara"

        payload = {
            "text": text,
            "input": text,
            "voice": actual_voice,
            "speed": 1.0,
            "response_format": "wav"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url_tts, json=payload, timeout=10.0)
                if response.status_code == 404:
                    response = await client.post(self.url_v1, json=payload, timeout=10.0)
                response.raise_for_status()
                print(f"Kokoro-82M Server Synthesized with voice '{actual_voice}': {len(response.content)} bytes")
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                import traceback
                print(f"Kokoro-82M Server Error ({self.url_tts}): {e}")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id,
                    error=f"Kokoro-82M Server connection error ({self.url_tts}): {e}"
                )


class HiggsAudioTTS:
    """Connects to ByteCompute's Higgs Audio V2.5 serverless TTS engine."""

    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/chat/completions"
        self.model_name = "boson-audio-multimodal-checkpoint-1200"
        self.api_key = api_key

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": text}
            ],
            "modalities": ["text", "audio"]
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                # Extract base64 audio data
                audio_data_base64 = result["choices"][0]["message"]["audio"]["data"]
                import base64
                audio_bytes = base64.b64decode(audio_data_base64)
                print(f"Higgs Audio TTS Synthesized: {len(audio_bytes)} bytes")
                return TTSResult(
                    audio_bytes=audio_bytes,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                import traceback
                print("Higgs Audio TTS Exception Traceback:")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id
                )



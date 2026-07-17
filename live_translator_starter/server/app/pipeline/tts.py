import httpx
from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_bytes: bytes
    content_type: str
    voice_id: str


class FakeTTS:
    """Placeholder for server-side TTS.

    The browser UI currently uses Web Speech API as a temporary TTS layer.
    """

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        return TTSResult(audio_bytes=b"", content_type="audio/wav", voice_id=voice_id)


class MossTTS:
    """Connects to Moss-TTS-v1.5 running on your company server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31240):
        self.url = f"http://{server_ip}:{port}/v1/audio/speech"
        self.model_name = "moss-tts"

    async def synthesize(self, text: str, voice_id: str) -> TTSResult:
        payload = {
            "model": self.model_name,
            "input": text,
            "voice": voice_id if voice_id else "default",
            "response_format": "wav"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=10.0)
                response.raise_for_status()
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                print(f"Moss TTS Connection Error: {e}")
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id
                )


class Qwen3TTS:
    """Connects to Qwen3-TTS-1.7B running on your company server."""

    def __init__(self, server_ip: str = "74.2.96.26", port: int = 31411):
        self.url = f"http://{server_ip}:{port}/v1/audio/speech"
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
                response = await client.post(self.url, json=payload, timeout=120.0)
                response.raise_for_status()
                print(f"Qwen3 TTS Synthesized: {len(response.content)} bytes")
                return TTSResult(
                    audio_bytes=response.content,
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except httpx.HTTPStatusError as e:
                import traceback
                print("Qwen3 TTS Exception Traceback:")
                print(f"Response Body: {e.response.text}")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id
                )
            except Exception as e:
                import traceback
                print("Qwen3 TTS General Exception Traceback:")
                traceback.print_exc()
                return TTSResult(
                    audio_bytes=b"",
                    content_type="audio/wav",
                    voice_id=voice_id
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



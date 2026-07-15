from pydantic import BaseModel, Field


class OfferRequest(BaseModel):
    sdp: str
    type: str
    source_language: str = Field(default="es", examples=["es"])
    target_language: str = Field(default="en", examples=["en"])
    model: str = Field(default="bytecompute/gemma-4-E4B-it", examples=["bytecompute/gemma-4-E4B-it"])
    asr_model: str = Field(default="Qwen/Qwen3-ASR-1.7B", examples=["Qwen/Qwen3-ASR-1.7B"])
    tts_model: str = Field(default="boson/higgs-audio-v2.5", examples=["boson/higgs-audio-v2.5"])
    voice_matching: bool = False


class OfferResponse(BaseModel):
    sdp: str
    type: str

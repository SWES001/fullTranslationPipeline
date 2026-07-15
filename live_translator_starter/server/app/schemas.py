from pydantic import BaseModel, Field


class OfferRequest(BaseModel):
    sdp: str
    type: str
    source_language: str = Field(default="es", examples=["es"])
    target_language: str = Field(default="en", examples=["en"])
    model: str = Field(default="tencent/Hy-MT2-1.8B", examples=["tencent/Hy-MT2-1.8B"])
    asr_model: str = Field(default="Qwen/Qwen3-ASR-1.7B", examples=["Qwen/Qwen3-ASR-1.7B"])
    voice_matching: bool = False


class OfferResponse(BaseModel):
    sdp: str
    type: str

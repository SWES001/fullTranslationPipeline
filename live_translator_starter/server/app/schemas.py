from pydantic import BaseModel, Field


class OfferRequest(BaseModel):
    sdp: str
    type: str
    source_language: str = Field(default="es", examples=["es"])
    target_language: str = Field(default="en", examples=["en"])
    model: str = Field(default="bytecompute/gemma-4-E4B-it", examples=["bytecompute/gemma-4-E4B-it"])
    asr_model: str = Field(default="openai/whisper-large-v3", examples=["openai/whisper-large-v3"])
    tts_model: str = Field(default="Kokoro-82M-Server", examples=["Kokoro-82M-Server"])
    voice_matching: bool = False


class OfferResponse(BaseModel):
    sdp: str
    type: str

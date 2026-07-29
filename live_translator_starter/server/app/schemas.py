from typing import Optional
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
    session_mode: str = Field(default="one_way", description="one_way or room")
    room_id: str = Field(default="Testing Room", description="Room name/ID when in room mode")
    client_id: Optional[str] = Field(default=None, description="Unique client device identifier")


class OfferResponse(BaseModel):
    sdp: str
    type: str


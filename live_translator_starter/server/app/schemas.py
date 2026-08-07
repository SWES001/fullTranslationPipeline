from typing import Optional
from pydantic import BaseModel, Field

from server.app.config import config


class OfferRequest(BaseModel):
    sdp: str
    type: str
    source_language: str = Field(default=config.default_source_language, examples=["es"])
    target_language: str = Field(default=config.default_target_language, examples=["en"])
    model: str = Field(default=config.translation_model, examples=["bytecompute/gemma-4-E4B-it"])
    asr_model: str = Field(default=config.asr_model, examples=["openai/whisper-large-v3"])
    tts_model: str = Field(default=config.tts_model, examples=["Kokoro-82M-Server"])
    voice_matching: bool = False
    session_mode: str = Field(default="one_way", description="one_way or room")
    room_id: str = Field(default="Testing Room", description="Room name/ID when in room mode")
    client_id: Optional[str] = Field(default=None, description="Unique client device identifier")


class OfferResponse(BaseModel):
    sdp: str
    type: str

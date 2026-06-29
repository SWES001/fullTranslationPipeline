from pydantic import BaseModel, Field


class OfferRequest(BaseModel):
    sdp: str
    type: str
    source_language: str = Field(default="ja", examples=["ja"])
    target_language: str = Field(default="en", examples=["en"])
    model: str = Field(default="fake", examples=["tencent/Hy-MT2-1.8B"])
    voice_matching: bool = False


class OfferResponse(BaseModel):
    sdp: str
    type: str

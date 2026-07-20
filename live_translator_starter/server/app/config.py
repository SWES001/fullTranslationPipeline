import os
from pydantic import BaseModel


class AppConfig(BaseModel):
    """Small app config object."""

    app_name: str = "Live Translator Starter"
    fake_chunk_seconds: float = 1.4
    max_session_seconds: int = 60 * 30
    asr_server_ip: str = os.getenv("ASR_SERVER_IP", "74.2.96.26")
    tts_server_ip: str = os.getenv("TTS_SERVER_IP", "74.2.96.26")
    translator_server_ip: str = os.getenv("TRANSLATOR_SERVER_IP", "74.2.96.26")


config = AppConfig()

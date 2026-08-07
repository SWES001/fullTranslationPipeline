import os
from pydantic import BaseModel


class AppConfig(BaseModel):
    """Small app config object."""

    app_name: str = "Live Translator Starter"
    fake_chunk_seconds: float = 1.4
    connection_timeout_seconds: int = int(os.getenv("CONNECTION_TIMEOUT_SECONDS", "30"))
    max_session_seconds: int = int(os.getenv("MAX_SESSION_SECONDS", str(60 * 30)))
    default_source_language: str = os.getenv("DEFAULT_SOURCE_LANGUAGE", "en")
    default_target_language: str = os.getenv("DEFAULT_TARGET_LANGUAGE", "en")
    translation_model: str = os.getenv("TRANSLATION_MODEL", "bytecompute/gemma-4-E4B-it")
    asr_model: str = os.getenv("ASR_MODEL", "openai/whisper-large-v3")
    tts_model: str = os.getenv("TTS_MODEL", "Kokoro-82M-Server")
    asr_server_ip: str = os.getenv("ASR_SERVER_IP", "74.2.96.26")
    tts_server_ip: str = os.getenv("TTS_SERVER_IP", "74.2.96.26")
    translator_server_ip: str = os.getenv("TRANSLATOR_SERVER_IP", "74.2.96.26")


config = AppConfig()

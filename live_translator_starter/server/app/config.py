from pydantic import BaseModel


class AppConfig(BaseModel):
    """Small app config object.

    Move these fields to pydantic-settings once you start reading real env vars.
    """

    app_name: str = "Live Translator Starter"
    fake_chunk_seconds: float = 1.4
    max_session_seconds: int = 60 * 30


config = AppConfig()

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceChoice:
    voice_id: str
    presentation: str
    pitch_bucket: str


class VoiceSelector:
    """Selects a target TTS voice.

    The starter does not infer gender. It returns a stable neutral voice.
    Later, add acoustic pitch profiling and a user preference such as
    masculine/feminine/neutral.
    """

    def select(self, target_language: str, voice_matching: bool = False) -> VoiceChoice:
        if target_language == "ja":
            return VoiceChoice("ja-neutral-medium-01", "neutral", "medium")
        return VoiceChoice("en-neutral-medium-01", "neutral", "medium")

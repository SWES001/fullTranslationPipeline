from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceChoice:
    voice_id: str
    presentation: str
    pitch_bucket: str


class VoiceSelector:
    """Selects a target TTS voice based on target language."""

    def select(self, target_language: str, voice_matching: bool = False) -> VoiceChoice:
        lang = (target_language or "en").lower().split("-")[0]
        if lang == "es":
            return VoiceChoice("ef_dora", "female", "medium")
        elif lang == "ja":
            return VoiceChoice("jf_alpha", "female", "medium")
        elif lang == "zh":
            return VoiceChoice("zf_xiaobei", "female", "medium")
        elif lang == "fr":
            return VoiceChoice("ff_siwis", "female", "medium")
        elif lang == "it":
            return VoiceChoice("if_sara", "female", "medium")
        else:
            return VoiceChoice("af_heart", "female", "medium")


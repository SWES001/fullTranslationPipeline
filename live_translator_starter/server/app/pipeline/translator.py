from dataclasses import dataclass
from typing import Protocol


class Translator(Protocol):
    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        ...


@dataclass
class FakeTranslator:
    """Fake translator used while the audio/WebRTC plumbing is being built."""

    model_name: str = "fake"

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        ja_to_en = {
            "えっと、明日の会議を午後三時に変更できますか？": "Um, can we move tomorrow's meeting to 3 p.m.?",
            "すみません、もう一回ゆっくり言ってもらえますか？": "Sorry, could you say that one more time slowly?",
            "この資料は今日中に確認します。": "I will review this document by the end of today.",
        }
        en_to_ja = {
            "Actually, can we move the meeting to next Wednesday instead?": "やっぱり、会議を来週の水曜日に変更できますか？",
            "Could you please say that one more time slowly?": "もう一度ゆっくり言っていただけますか？",
            "I will review this document by the end of today.": "この資料は今日中に確認します。",
        }
        if source_language == "ja" and target_language == "en":
            return ja_to_en.get(text, f"[fake EN translation] {text}")
        if source_language == "en" and target_language == "ja":
            return en_to_ja.get(text, f"[fake JA translation] {text}")
        return text

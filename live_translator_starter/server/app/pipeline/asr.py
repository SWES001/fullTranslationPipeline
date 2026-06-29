from dataclasses import dataclass, field
from itertools import cycle
from typing import Iterable, Protocol


@dataclass
class ASRResult:
    text: str
    is_final: bool
    confidence: float
    language: str


class ASR(Protocol):
    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        ...


@dataclass
class FakeASR:
    """Fake ASR used to test the app before adding a real speech model."""

    _ja_samples: object = field(default_factory=lambda: cycle([
        "えっと、明日の会議を午後三時に変更できますか？",
        "すみません、もう一回ゆっくり言ってもらえますか？",
        "この資料は今日中に確認します。",
    ]))
    _en_samples: object = field(default_factory=lambda: cycle([
        "Actually, can we move the meeting to next Wednesday instead?",
        "Could you please say that one more time slowly?",
        "I will review this document by the end of today.",
    ]))

    async def transcribe_pcm(self, frames: Iterable[object], source_language: str) -> ASRResult:
        text = next(self._ja_samples if source_language == "ja" else self._en_samples)
        return ASRResult(
            text=text,
            is_final=True,
            confidence=0.99,
            language=source_language,
        )

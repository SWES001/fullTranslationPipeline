from dataclasses import dataclass, field
from typing import Optional

from server.app.pipeline.asr import ASRResult


@dataclass
class StableTextBuffer:
    """Decides which ASR text is safe to translate and speak.

    A real implementation should compare consecutive ASR hypotheses and
    commit only the stable prefix. The starter commits final fake utterances.
    """

    committed_texts: set[str] = field(default_factory=set)

    def commit(self, result: ASRResult) -> Optional[str]:
        if not result.is_final:
            return None
        cleaned = result.text.strip()
        if not cleaned or cleaned in self.committed_texts:
            return None
        self.committed_texts.add(cleaned)
        return cleaned

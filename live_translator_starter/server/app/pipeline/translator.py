import httpx
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

class HyMT2Translator:
    """Connects to your company's Hy-MT2-1.8B vLLM translation server."""
    def __init__(self, server_ip: str = "74.2.96.26", port: int = 32232):
        self.url = f"http://{server_ip}:{port}/v1/chat/completions"
        self.model_name = "/model-weights"
        self.api_key = "sk-proj-8-W-hNfM9cJ_t_gL4pQ4k_t2sXzY9uW9O0iZ7bA"

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        # Map short language codes to full names for the model's instructions
        lang_names = {
            "en": "English",
            "ja": "Japanese",
            "es": "Spanish",
            "zh": "Mandarin Chinese"
        }
        src = lang_names.get(source_language, "English")
        tgt = lang_names.get(target_language, "Japanese")
        
        prompt = (
            f"Translate the following {src} text into {tgt}. "
            "Only return the translated text itself, without any introduction, explanation, or quotes.\n\n"
            f"{text}"
        )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 256,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                translation = result["choices"][0]["message"]["content"].strip()
                return translation
            except Exception as e:
                print(f"Translation Error: {e}")
                return f"[Translation Error: {e}] {text}"


class ByteComputeTranslator:
    """Connects to ByteCompute's serverless AI API gateway."""
    def __init__(self, api_key: str = "bytecompute_RvJjDWOF_LhtSI4TXqabrSCqQHcMfxNF"):
        self.url = "https://us-01.bytecompute.ai/v1/chat/completions"
        self.model_name = "gemma-4-E4B-it"
        self.api_key = api_key

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        # Map short language codes to full names for the model's instructions
        lang_names = {
            "en": "English",
            "ja": "Japanese",
            "es": "Spanish",
            "zh": "Mandarin Chinese"
        }
        src = lang_names.get(source_language, "English")
        tgt = lang_names.get(target_language, "Japanese")
        
        if target_language == "ja":
            instruction = f"Translate the following {src} text into natural Japanese. Transliterate all foreign names and proper nouns into Katakana (e.g. Ben -> ベン, Toronto -> トロント). Do not leave English letters in the translation."
        elif target_language == "zh":
            instruction = f"Translate the following {src} text into natural Mandarin Chinese. Transliterate all foreign names and proper nouns into Chinese Hanzi characters (e.g. Ben -> 本, Toronto -> 多伦多). Do not leave English letters in the translation."
        else:
            instruction = f"Translate the following {src} text into {tgt}."
        
        prompt = (
            f"{instruction} "
            "Return ONLY the translated text itself, without any introduction, explanation, or quotes.\n\n"
            f"{text}"
        )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 256,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                translation = result["choices"][0]["message"]["content"].strip()
                print(f"Gemma 4 Translated: '{translation}'")
                return translation
            except Exception as e:
                import traceback
                print("ByteCompute Translator Exception Traceback:")
                traceback.print_exc()
                return f"[Translation Error: {e}] {text}"


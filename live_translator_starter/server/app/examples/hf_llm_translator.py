"""Optional Transformers translator wrapper.

This is not imported by the starter server. Copy the parts you need into
`server/app/pipeline/translator.py` when you are ready to test a local model.

Install optional dependencies first:

    pip install torch transformers accelerate sentencepiece

Example model IDs to try:

    tencent/Hy-MT2-1.8B
    cyberagent/CAT-Translate-3.3b
    Qwen/Qwen3-8B
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class HFChatTranslator:
    model_id: str
    max_new_tokens: int = 160

    def __post_init__(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        return await asyncio.to_thread(self._translate_sync, text, source_language, target_language)

    def _translate_sync(self, text: str, source_language: str, target_language: str) -> str:
        prompt = (
            f"Translate the following {source_language} text into {target_language}.\n"
            "Only output the translation. Do not explain.\n\n"
            f"{text}"
        )
        messages = [{"role": "user", "content": prompt}]
        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self.model.device)

        with self.torch.no_grad():
            output = self.model.generate(
                inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                temperature=0.0,
            )

        generated = output[0][inputs.shape[-1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

DEFAULT_MODEL = "gemma3:4b"
DEFAULT_BASE_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class LLMSettings:
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = "ollama"

    @classmethod
    def from_environment(cls) -> "LLMSettings":
        return cls(
            model=os.getenv("LETTER_AI_MODEL", DEFAULT_MODEL),
            base_url=os.getenv("LETTER_AI_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.getenv("LETTER_AI_API_KEY", "ollama"),
        )


class LetterLLM:
    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or LLMSettings.from_environment()
        self.client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The LLM returned an empty response.")
        return content.strip()

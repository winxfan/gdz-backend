from __future__ import annotations

import logging
from typing import Any, Tuple

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class YandexGPTService:
    def __init__(self, api_key: str, project: str | None, prompt_id: str) -> None:
        self.prompt_id = prompt_id
        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.yandex_gpt_base_url,
            project=project,
        )

    def generate(self, input_text: str) -> Tuple[str, dict[str, Any]]:
        if not input_text.strip():
            raise ValueError("Empty input text for Yandex GPT")
        logger.info("yandex_gpt.generate: text_len=%s", len(input_text))
        chunks: list[str] = []
        with self.client.responses.stream(
            prompt={"id": self.prompt_id},
            input=input_text,
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    chunks.append(event.delta)
                elif event.type == "response.error":
                    raise RuntimeError(f"Yandex GPT error: {event.error}")
            final_response = stream.get_final_response()
        text = "".join(chunks).strip()
        meta = {
            "responseId": getattr(final_response, "id", None),
            "usage": getattr(final_response, "usage", None),
        }
        return text, meta


_gpt_service: YandexGPTService | None = None


def get_gpt_service() -> YandexGPTService:
    global _gpt_service
    if _gpt_service is None:
        if not settings.yandex_gpt_api_key or not settings.yandex_gpt_prompt_id:
            raise RuntimeError("Yandex GPT settings are not configured")
        _gpt_service = YandexGPTService(
            api_key=settings.yandex_gpt_api_key,
            project=settings.yandex_gpt_project_id,
            prompt_id=settings.yandex_gpt_prompt_id,
        )
    return _gpt_service



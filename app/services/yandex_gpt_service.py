from __future__ import annotations

import json
import logging
from typing import Any, Tuple

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class YandexGPTService:
    def __init__(self, api_key: str, project: str | None, prompt_id: str) -> None:
        if not api_key:
            raise RuntimeError("YANDEX_GPT_API_KEY is not configured")
        if not prompt_id:
            raise RuntimeError("YANDEX_GPT_PROMPT_ID is not configured")

        self.prompt_id = prompt_id
        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.yandex_gpt_base_url,
            project=project,
        )

        if not hasattr(self.client, "responses"):
            raise RuntimeError(
                "Installed openai package does not support Responses API. "
                "Please install openai>=1.0 inside the runtime environment."
            )

    def generate(self, input_text: str) -> Tuple[str, dict[str, Any]]:
        if not input_text.strip():
            raise ValueError("Empty input text for Yandex GPT")
        logger.info("yandex_gpt.generate: text_len=%s", len(input_text))
        response = self.client.responses.create(
            prompt={"id": self.prompt_id},
            input=input_text,
        )

        text = (getattr(response, "output_text", "") or "").strip()
        usage = getattr(response, "usage", None)
        response_id = getattr(response, "id", None)
        logger.info(
            "yandex_gpt.generate: response_id=%s generated_len=%s usage=%s meta=%s",
            response_id,
            len(text or ""),
            usage,
            json.dumps(getattr(response, "model_dump", lambda: {})(), ensure_ascii=False)
            if hasattr(response, "model_dump")
            else str(response),
        )
        meta = {
            "responseId": response_id,
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else usage,
        }
        return text, meta


_gpt_service: YandexGPTService | None = None


def get_gpt_service() -> YandexGPTService:
    global _gpt_service
    if _gpt_service is None:
        _gpt_service = YandexGPTService(
            api_key=settings.yandex_ocr_api_key or "",
            project=settings.yandex_gpt_project_id,
            prompt_id=settings.yandex_gpt_prompt_id or "",
        )
    return _gpt_service



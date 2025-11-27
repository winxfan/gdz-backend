from __future__ import annotations

import base64
import logging
import time
from typing import Any, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OCR_API_URL = "https://ocr.api.cloud.yandex.net/ocr/v1"
OPERATIONS_API_URL = "https://operation.api.cloud.yandex.net/operations"


class YandexOCRService:
    def __init__(self, api_key: str, folder_id: str | None = None) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
        }
        if self.folder_id:
            headers["x-folder-id"] = self.folder_id
        return headers

    def recognize(
        self,
        content: bytes,
        mime_type: str | None = None,
        language_codes: list[str] | None = None,
        poll_timeout: float = 60.0,
        poll_interval: float = 2.0,
    ) -> Tuple[str, dict[str, Any]]:
        if not content:
            raise ValueError("Empty content provided for OCR")
        payload = {
            "content": base64.b64encode(content).decode(),
            "mimeType": mime_type or "image/jpeg",
            "languageCodes": language_codes or ["ru"],
        }
        headers = self._headers()
        logger.info("yandex_ocr.recognize: sending request mime=%s size=%s", payload["mimeType"], len(content))
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{OCR_API_URL}/recognizeTextAsync", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            operation_id = data.get("id")
            if not operation_id:
                raise RuntimeError("Yandex OCR did not return operation id")
            self._wait_operation(client, headers, operation_id, poll_timeout, poll_interval)
            recognition = self._get_recognition(client, headers, operation_id)

        text_annotation = (
            recognition.get("textAnnotation")
            or recognition.get("result", {}).get("textAnnotation")
            or {}
        )
        full_text = (
            text_annotation.get("fullText")
            or recognition.get("fullText")
            or recognition.get("result", {}).get("fullText")
            or ""
        )
        if not full_text:
            raw = recognition.get("raw") or {}
            full_text = (
                raw.get("result", {})
                .get("textAnnotation", {})
                .get("fullText")
                or ""
            )
        logger.info("yandex_ocr.recognize: full_text_len=%s", len(full_text or ""))
        
        return full_text, {
            "operationId": operation_id,
            "textAnnotation": text_annotation,
            "raw": recognition,
        }

    def _wait_operation(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        operation_id: str,
        poll_timeout: float,
        poll_interval: float,
    ) -> None:
        deadline = time.time() + poll_timeout
        while True:
            resp = client.get(f"{OPERATIONS_API_URL}/{operation_id}", headers=headers)
            resp.raise_for_status()
            body = resp.json()
            if body.get("done"):
                if "error" in body:
                    raise RuntimeError(f"Yandex OCR operation error: {body['error']}")
                logger.info("yandex_ocr.operation_done: operation_id=%s", operation_id)
                return
            if time.time() > deadline:
                raise TimeoutError("Yandex OCR operation timeout")
            time.sleep(poll_interval)

    def _get_recognition(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        operation_id: str,
    ) -> dict[str, Any]:
        resp = client.get(f"{OCR_API_URL}/getRecognition", params={"operationId": operation_id}, headers=headers)
        resp.raise_for_status()
        return resp.json()


_ocr_service: YandexOCRService | None = None


def get_ocr_service() -> YandexOCRService:
    global _ocr_service
    if _ocr_service is None:
        if not settings.yandex_ocr_api_key:
            raise RuntimeError("YANDEX_OCR_API_KEY is not configured")
        _ocr_service = YandexOCRService(
            api_key=settings.yandex_ocr_api_key,
            folder_id=settings.yandex_cloud_folder_id,
        )
    return _ocr_service



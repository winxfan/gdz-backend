import base64
import requests
from typing import Any, Dict
import uuid
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

def _auth_header() -> str:
	if not settings.yookassa_shop_id or not settings.yookassa_api_key:
		raise RuntimeError("YooKassa credentials not configured")
	basic = f"{settings.yookassa_shop_id}:{settings.yookassa_api_key}".encode()
	return "Basic " + base64.b64encode(basic).decode()


def create_payment(order_id: str, amount_rub: float, description: str, return_url: str, email: str | None = None, anon_user_id: str | None = None, user_id: str | None = None, extra_metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
	"""Создать платеж и получить confirmation_url.
	Документация YooKassa: POST /v3/payments
	"""
	url = f"{settings.yookassa_api_base}/v3/payments"
	# Определим данные покупателя для чека: email обязателен (фоллбэк если нет), full_name добавляем опционально
	fallback_email = getattr(settings, "yookassa_fallback_receipt_email", None)
	receipt_email = email or fallback_email or "no-email@kreatum.ai"
	receipt_customer: Dict[str, Any] = {"email": receipt_email}
	tax_system_code = getattr(settings, "yookassa_tax_system_code", 1)
	vat_code = getattr(settings, "yookassa_vat_code", 1)
	metadata: Dict[str, Any] = {
		"order_id": order_id,
		"email": email,
		"anonUserId": anon_user_id,
		"user_id": user_id,
	}
	if extra_metadata and isinstance(extra_metadata, dict):
		try:
			metadata.update(extra_metadata)
		except Exception:
			pass
	payload_base: Dict[str, Any] = {
		"amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
		"capture": True,
		"description": description,
		"metadata": metadata,
		"confirmation": {"type": "redirect", "return_url": return_url},
	}
	# Сформируем payload с чеком (всегда включаем receipt)
	payload: Dict[str, Any] = dict(payload_base)
	payload["receipt"] = {
		"customer": receipt_customer,
		"tax_system_code": tax_system_code,
		"items": [
			{
				"description": description[:128] or "Оживление видео",
				"amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
				"quantity": "1.00",
				"vat_code": vat_code,
				"payment_subject": "service",
				"payment_mode": "full_payment",
			}
		]
	}
	headers = {
		"Authorization": _auth_header(),
		# уникальный ключ на каждый запрос (а не order_id)
		"Idempotence-Key": str(uuid.uuid4()),
		"Content-Type": "application/json",
	}
	logger.info(
		"YooKassa create_payment: order_id=%s amount=%.2f include_receipt=%s return_url_present=%s customer_keys=%s",
		order_id, amount_rub, True, bool(return_url), list(receipt_customer.keys())
	)
	resp = requests.post(url, json=payload, headers=headers, timeout=20)
	if not resp.ok:
		err_text = None
		try:
			err_text = resp.text
		except Exception:
			err_text = None
		# Если ошибка из-за чека — логируем подробности, но не убираем чек (магазин требует чек)
		text_lower = (err_text or "").lower()
		if resp.status_code == 400 and "receipt" in text_lower:
			logger.error(
				"YooKassa 400 invalid receipt: order_id=%s customer_keys=%s vat=%s tax_system=%s text=%s",
				order_id, list(receipt_customer.keys()), vat_code, tax_system_code, (err_text or "")[:500]
			)
		# вернём подробности ошибки вызывающей стороне
		try:
			return {"error": {"status": resp.status_code, "text": err_text or ""}}
		except Exception:
			resp.raise_for_status()
	data = resp.json()
	confirmation_url = data.get("confirmation", {}).get("confirmation_url")
	payment_id = data.get("id")
	if not confirmation_url or not payment_id:
		raise ValueError("YooKassa: confirmation_url or payment id missing")
	return {"payment_id": payment_id, "payment_url": confirmation_url, "raw": data}



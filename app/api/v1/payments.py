from __future__ import annotations

import uuid
from decimal import Decimal
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 fallback
    from pydantic import BaseModel, Field  # type: ignore
    ConfigDict = None  # type: ignore
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Transaction, User
from app.services.yookassa_service import create_payment as create_yookassa_payment
from app.core.config import settings
from app.services.tariff_catalog import get_tariff

router = APIRouter(prefix="/payments", tags=["Payments"]) 

logger = logging.getLogger(__name__)

if ConfigDict:
    class _PopulateByNameModel(BaseModel):
        model_config = ConfigDict(populate_by_name=True, ser_json_timedelta="iso8601")
else:  # pragma: no cover
    class _PopulateByNameModel(BaseModel):
        class Config:
            allow_population_by_field_name = True


class CreatePaymentIntentRequest(_PopulateByNameModel):
    user_id: uuid.UUID = Field(alias="userId")
    tariff_id: str = Field(alias="tariffId")
    provider: str | None = Field(default=None)
    description: str | None = None


class PaymentIntentResponse(_PopulateByNameModel):
    id: str
    provider: str
    amountRub: float
    currency: str
    paymentUrl: str | None = None
    reference: str
    paymentId: str | None = None
    tariff_id: str = Field(alias="tariffId")
    tokens: float


@router.post("/intents", response_model=PaymentIntentResponse)
def create_payment_intent(payload: CreatePaymentIntentRequest, db: Session = Depends(get_db), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> PaymentIntentResponse:
    provider = payload.provider or "yookassa"
    tariff = get_tariff(payload.tariff_id)
    if not tariff:
        logger.warning("Tariff not found for payment intent: tariff_id=%s", payload.tariff_id)
        raise HTTPException(status_code=404, detail="Tariff not found")

    amount_rub_dec = Decimal(str(tariff["price_rub"]))
    tokens_dec = Decimal(str(tariff["tokens"]))
    plan = tariff["title"]
    description = (payload.description or plan).strip()
    logger.info(
        "Create payment intent: userId=%s tariff_id=%s amountRub=%s tokens=%s provider=%s idempotency=%s",
        payload.user_id, payload.tariff_id, amount_rub_dec, tokens_dec, provider, idempotency_key
    )

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        logger.warning("User not found for payment intent: userId=%s", payload.user_id)
        raise HTTPException(status_code=404, detail="User not found")

    reference = idempotency_key or uuid.uuid4().hex
    txn = Transaction(
        user_id=user.id,
        type="gateway_payment",
        provider=provider,
        status="pending",
        amount_rub=amount_rub_dec,
        currency="RUB",
        plan=plan,
        reference=reference,
        meta={"intent": True, "tariffId": payload.tariff_id, "tokens": float(tokens_dec)},
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    logger.info(
        "Payment intent transaction created: txn_id=%s reference=%s user_id=%s amount_rub=%s tokens=%s provider=%s",
        txn.id, reference, user.id, amount_rub_dec, tokens_dec, provider
    )

    # Реальная генерация ссылки YooKassa
    payment_url = None
    payment_id = None
    if provider == "yookassa":
        base = settings.frontend_return_url_base or ""
        return_url = f"{base}/balance.html" if base else ""
        desc = (description or plan or "Пополнение баланса").strip()
        try:
            logger.info(
                "Calling YooKassa create_payment: order_id=%s amount_rub=%s return_url=%s has_email=%s",
                txn.id, amount_rub_dec, return_url, bool(user.email)
            )
            yk = create_yookassa_payment(
                order_id=str(txn.id),
                amount_rub=float(amount_rub_dec),
                description=desc,
                return_url=return_url,
                email=user.email,
                anon_user_id=user.anon_user_id,
                user_id=str(user.id),
                extra_metadata={
                    "topup": True,
                    "tariff_id": tariff["id"],
                    "tariff_title": plan,
                    "tokens": float(tokens_dec),
                    "credit_rub": float(tokens_dec),
                    "original_amount_rub": float(amount_rub_dec),
                },
            )
            if "error" in yk:
                logger.error("YooKassa error for order_id=%s: %s", txn.id, yk.get("error"))
                raise HTTPException(status_code=502, detail=f"YooKassa error: {yk['error']}")
            payment_url = yk.get("payment_url")
            payment_id = yk.get("payment_id")
            # обогатим мета
            meta = txn.meta or {}
            meta.update({
                "yookassa": {"paymentId": payment_id, "paymentUrl": payment_url, "raw": yk.get("raw")},
                "topup": True,
                "tariffId": tariff["id"],
                "tariffTitle": plan,
                "tokens": float(tokens_dec),
                "priceRub": float(amount_rub_dec),
            })
            txn.meta = meta
            db.commit()
            db.refresh(txn)
            logger.info(
                "YooKassa payment created: order_id=%s payment_id=%s confirmation_url_present=%s",
                txn.id, payment_id, bool(payment_url)
            )
            # Если email отсутствует — уведомим Telegram-бот о ссылке на оплату
            if not user.email and payment_url:
                try:
                    from app.services.telegram_service import notify_payment_receipt
                    notify_payment_receipt(
                        user_id=str(user.id),
                        payment_url=payment_url,
                        payment_id=payment_id,
                        amount_rub=float(amount_rub_dec),
                        order_id=str(txn.id),
                        provider="yookassa",
                    )
                    logger.info("payments.intent: telegram receipt notified for txn_id=%s", txn.id)
                except Exception:
                    logger.exception("payments.intent: failed to notify telegram receipt for txn_id=%s", txn.id)
        except HTTPException as e:
            logger.exception("HTTPException in create_payment_intent for order_id=%s: %s", txn.id, getattr(e, "detail", e))
            raise
        except Exception as e:
            logger.exception("YooKassa create_payment failed for order_id=%s", txn.id)
            raise HTTPException(status_code=502, detail=f"YooKassa create payment failed: {e}")
    else:
        # При необходимости поддержать другие провайдеры
        logger.info("Using provider=%s for payment intent (non-YooKassa), reference=%s", provider, reference)
        payment_url = f"https://pay.example/{provider}?ref={reference}"

    resp = {
        "id": str(txn.id),
        "provider": provider,
        "amountRub": float(amount_rub_dec),
        "currency": txn.currency,
        "paymentUrl": payment_url,
        "reference": reference,
        "paymentId": payment_id,
        "tariffId": tariff["id"],
        "tokens": float(tokens_dec),
    }
    logger.info(
        "Payment intent response: txn_id=%s provider=%s amountRub=%s tokens=%s paymentId=%s has_url=%s",
        txn.id, provider, resp["amountRub"], resp["tokens"], payment_id, bool(payment_url)
    )
    return resp





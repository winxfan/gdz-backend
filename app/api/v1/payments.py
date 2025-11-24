from __future__ import annotations

import uuid
from decimal import Decimal
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Transaction, User
from app.services.yookassa_service import create_payment as create_yookassa_payment
from app.core.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"]) 

logger = logging.getLogger(__name__)

@router.post("/intents")
def create_payment_intent(payload: dict, db: Session = Depends(get_db), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict:
    user_id = payload.get("userId")
    amount_rub = payload.get("amountRub")
    provider = payload.get("provider") or "yookassa"
    plan = payload.get("plan")
    description = payload.get("description")
    logger.info(
        "Create payment intent: userId=%s amountRub=%s provider=%s plan=%s idempotency=%s",
        user_id, amount_rub, provider, plan, idempotency_key
    )
    if not user_id or amount_rub is None:
        logger.warning("Missing required fields for payment intent: payload=%s", {k: payload.get(k) for k in ["userId", "amountRub", "provider", "plan"]})
        raise HTTPException(status_code=400, detail="userId and amountRub are required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("User not found for payment intent: userId=%s", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    reference = idempotency_key or uuid.uuid4().hex
    txn = Transaction(
        user_id=user.id,
        type="gateway_payment",
        provider=provider,
        status="pending",
        amount_rub=Decimal(str(amount_rub)),
        currency="RUB",
        plan=plan,
        reference=reference,
        meta={"intent": True},
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    logger.info(
        "Payment intent transaction created: txn_id=%s reference=%s user_id=%s amount_rub=%s provider=%s",
        txn.id, reference, user.id, amount_rub, provider
    )

    # Рассчёт бонусов для пополнения баланса
    credit_rub_dec = Decimal(str(amount_rub))
    if provider == "yookassa":
        # Точные акции по суммам
        if Decimal("100") == credit_rub_dec:
            credit_rub_dec = Decimal("100")
        elif Decimal("500") == credit_rub_dec:
            credit_rub_dec = Decimal("575")
        elif Decimal("1000") == credit_rub_dec:
            credit_rub_dec = Decimal("1250")
        # иначе без бонуса — оставляем исходную сумму

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
                txn.id, amount_rub, return_url, bool(user.email)
            )
            yk = create_yookassa_payment(
                order_id=str(txn.id),
                amount_rub=float(amount_rub),
                description=desc,
                return_url=return_url,
                email=user.email,
                anon_user_id=user.anon_user_id,
                user_id=str(user.id),
                extra_metadata={
                    "topup": True,
                    "credit_rub": float(credit_rub_dec),
                    "original_amount_rub": float(amount_rub),
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
                "creditRub": float(credit_rub_dec),
                "originalAmountRub": float(amount_rub),
                "bonusRub": float(credit_rub_dec - Decimal(str(amount_rub))),
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
                        amount_rub=float(amount_rub),
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
        "amountRub": float(txn.amount_rub or 0),
        "currency": txn.currency,
        "paymentUrl": payment_url,
        "reference": reference,
        "paymentId": payment_id,
    }
    logger.info(
        "Payment intent response: txn_id=%s provider=%s amountRub=%s paymentId=%s has_url=%s",
        txn.id, provider, resp["amountRub"], payment_id, bool(payment_url)
    )
    return resp





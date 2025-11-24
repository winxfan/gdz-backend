from decimal import Decimal
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import WebhookLog, Transaction, User, Job, Model
from app.services.email_service import send_email_with_links
from app.services.fal import submit_generation

router = APIRouter(prefix="/webhooks", tags=["Webhooks"]) 


@router.post("/payments/{provider}")
async def payments_webhook(provider: str, request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.json()

    # логируем событие
    log = WebhookLog(event_type=f"payments:{provider}", payload=payload)
    db.add(log)
    db.commit()

    # Специальная обработка YooKassa оплаты заказа (одноразовая генерация)
    if provider == "yookassa":
        obj = payload.get("object") or {}
        status = obj.get("status") or payload.get("status")
        metadata = obj.get("metadata") or {}
        order_id = metadata.get("order_id") or payload.get("order_id")
        amount_val = None
        try:
            amount_val = obj.get("amount", {}).get("value")
        except Exception:
            amount_val = None

        if order_id and status in ("succeeded", "succeeded_with_3ds", "waiting_for_capture"):
            job = db.query(Job).filter(Job.order_id == order_id).first()
            if job:
                # 1) обновим финансы/флаги оплаты
                if amount_val is not None:
                    try:
                        job.price_rub = Decimal(str(amount_val))
                    except Exception:
                        pass
                job.is_paid = True
                job.status = "queued"
                info = job.payment_info or {}
                info.update({"yookassa": obj})
                job.payment_info = info
                db.commit()
                db.refresh(job)

                # 2) зафиксируем транзакцию шлюза
                try:
                    txn = Transaction(
                        user_id=job.user_id,
                        job_id=job.id,
                        type="gateway_payment",
                        provider="yookassa",
                        status="success" if str(status).startswith("succeeded") else "pending",
                        amount_rub=Decimal(str(amount_val)) if amount_val is not None else None,
                        currency="RUB",
                        reference=obj.get("id"),
                        meta=payload,
                    )
                    db.add(txn)
                    db.commit()
                except Exception:
                    db.rollback()

                # 3) Запустим генерацию в FAL (по формату модели)
                try:
                    model = None
                    if job.model_id:
                        model = db.query(Model).filter(Model.id == job.model_id).first()
                    fmt_from = (model.format_from or "").strip().lower() if model and model.format_from else None
                    fmt_to = (model.format_to or "").strip().lower() if model and model.format_to else None
                    options = model.options or {} if model and isinstance(model.options, dict) else {}
                    endpoint = options.get("fal_endpoint") or options.get("endpoint") if isinstance(options, dict) else None
                    if not endpoint and model and model.name:
                        endpoint = model.name

                    input_objects = job.input if isinstance(job.input, list) else []

                    def _extract_prompt(input_objects_local: list | None) -> str | None:
                        if not isinstance(input_objects_local, list):
                            return None
                        for it in input_objects_local:
                            if not isinstance(it, dict):
                                continue
                            if isinstance(it.get("prompt"), str) and it.get("prompt").strip():
                                return it.get("prompt").strip()
                            if it.get("name") == "prompt":
                                val = it.get("value")
                                if isinstance(val, str) and val.strip():
                                    return val.strip()
                        for it in input_objects_local:
                            if isinstance(it, dict) and it.get("type") == "text":
                                val = it.get("value")
                                if isinstance(val, str) and val.strip():
                                    return val.strip()
                        return None

                    def _extract_image_url(input_objects_local: list | None) -> str | None:
                        if not isinstance(input_objects_local, list):
                            return None
                        for it in input_objects_local:
                            if not isinstance(it, dict):
                                continue
                            for key in ("url", "image_url"):
                                val = it.get(key)
                                if isinstance(val, str) and val:
                                    return val
                            val = it.get("value")
                            if isinstance(val, str) and val:
                                return val
                            if isinstance(val, list):
                                for cand in val:
                                    if isinstance(cand, str) and cand:
                                        return cand
                        return None

                    def _extract_extra_args(input_objects_local: list | None) -> dict:
                        args: dict = {}
                        if not isinstance(input_objects_local, list):
                            return args
                        for it in input_objects_local:
                            if not isinstance(it, dict):
                                continue
                            name = it.get("name")
                            typ = it.get("type")
                            if not isinstance(name, str) or name in ("prompt", "image_url"):
                                continue
                            if typ == "upload_zone":
                                continue
                            if "value" in it:
                                val = it.get("value")
                                if isinstance(val, (str, int, float, bool)) and val != "":
                                    args[name] = val
                        return args

                    prompt = _extract_prompt(input_objects) or ((job.meta or {}).get("prompt") if isinstance(job.meta, dict) else None) or ""
                    image_url = _extract_image_url(input_objects)
                    extra_args = _extract_extra_args(input_objects)

                    # Выбираем сценарий
                    if fmt_from == "image" and fmt_to == "video":
                        local_prompt = prompt or "Animate this image"
                        fal_resp = submit_generation(
                            image_url=image_url,
                            prompt=local_prompt,
                            order_id=str(job.id),
                            item_index=0,
                            anon_user_id=None,
                            endpoint=endpoint,
                            extra_args=extra_args,
                        )
                    elif fmt_from == "text" and fmt_to == "image":
                        fal_resp = submit_generation(
                            image_url=None,
                            prompt=prompt or "Generate image",
                            order_id=str(job.id),
                            item_index=0,
                            anon_user_id=None,
                            endpoint=endpoint,
                            extra_args=extra_args,
                        )
                    elif fmt_from == "image" and fmt_to == "image":
                        fal_resp = submit_generation(
                            image_url=image_url,
                            prompt=prompt or "",
                            order_id=str(job.id),
                            item_index=0,
                            anon_user_id=None,
                            endpoint=endpoint,
                            extra_args=extra_args,
                        )
                    elif fmt_from == "text" and fmt_to == "video":
                        fal_resp = submit_generation(
                            image_url=None,
                            prompt=prompt or "Generate video",
                            order_id=str(job.id),
                            item_index=0,
                            anon_user_id=None,
                            endpoint=endpoint,
                            extra_args=extra_args,
                        )
                    else:
                        fal_resp = None

                    if fal_resp and isinstance(fal_resp, dict):
                        meta = job.meta or {}
                        meta.update({"fal": {"requestId": fal_resp.get("request_id"), "modelId": fal_resp.get("model_id")}})
                        job.meta = meta
                        if fal_resp.get("request_id"):
                            job.request_id = str(fal_resp.get("request_id"))
                        db.commit()
                        db.refresh(job)
                except Exception:
                    # Если не удалось запустить FAL — оставляем статус queued; поллер или повторная оплата не требуются
                    db.rollback()

                # Не отправляем email сейчас — письмо уйдет после завершения в поллере
                return {"ok": True}
            else:
                # Пополнение баланса (не привязано к job): берём user_id из metadata
                user_id_meta = metadata.get("user_id")
                if user_id_meta and amount_val is not None and str(status).startswith("succeeded"):
                    user = db.query(User).filter(User.id == user_id_meta).first()
                    if user:
                        try:
                            # Рассчитаем сумму для зачисления с учетом бонуса (если передана в metadata)
                            credit_rub_val = metadata.get("credit_rub")
                            credit_rub_dec = None
                            try:
                                credit_rub_dec = Decimal(str(credit_rub_val)) if credit_rub_val is not None else Decimal(str(amount_val))
                            except Exception:
                                credit_rub_dec = Decimal(str(amount_val))
                            txn = Transaction(
                                user_id=user.id,
                                job_id=None,
                                type="gateway_payment",
                                provider="yookassa",
                                status="success",
                                amount_rub=Decimal(str(amount_val)),
                                currency="RUB",
                                reference=obj.get("id"),
                                meta=payload,
                            )
                            db.add(txn)
                            # Зачисление средств на баланс (у нас баланс хранится в тех же "токенах", что и списание — фактически RUB)
                            user.balance_tokens = (user.balance_tokens or 0) + credit_rub_dec
                            txn.tokens_delta = credit_rub_dec
                            db.commit()
                            # Оповестим бота об успешном пополнении
                        except Exception:
                            db.rollback()
                        return {"ok": True}

    # Простейшая универсальная обработка: если в payload есть userId и amountRub — записываем транзакцию (без токенов)
    user_id = payload.get("userId") or payload.get("user_id")
    amount_rub = payload.get("amountRub") or payload.get("amount_rub")
    plan = payload.get("plan")
    reference = payload.get("reference")
    if user_id and amount_rub:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            txn = Transaction(
                user_id=user.id,
                type="gateway_payment",
                provider=provider,
                status="success",
                amount_rub=Decimal(str(amount_rub)),
                currency="RUB",
                plan=plan,
                reference=reference,
                meta=payload,
            )
            db.add(txn)
            db.commit()

    return {"ok": True}


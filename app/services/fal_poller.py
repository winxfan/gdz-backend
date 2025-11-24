from __future__ import annotations

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.db.models import Job, Model
from app.services.fal import get_request_status, get_request_response, extract_media_url, fetch_bytes
from app.services.s3_utils import s3_key_for_video, upload_bytes, get_file_url_with_expiry
from app.core.config import settings
from app.services.telegram_service import notify_job_event
from app.services.email_service import send_email_with_links


# Используем uvicorn.error, чтобы гарантировать попадание в стандартные логи сервера
logger = logging.getLogger("uvicorn.error")


def _pick_media_url(request_status: dict, request_response: dict) -> Optional[str]:
    # При использовании fal-client достаточно разобрать response
    u = extract_media_url(request_response)
    if u:
        return u
    return None


def run_poller(interval_seconds: int = 20) -> None:
    """Бесконечный цикл поллинга очереди FAL для задач в статусах queued/processing."""
    logger.info("fal.poll: started interval=%ss", interval_seconds)
    while True:
        try:
            logger.info("fal.poll: tick start")
            db: Session = SessionLocal()
            try:
                # Выбираем оплаченные задачи, ожидающие исполнения
                jobs = (
                    db.query(Job)
                    .filter(Job.is_paid.is_(True))
                    .filter(Job.status.in_(["queued", "processing"]))
                    .all()
                )
                logger.info("fal.poll: active jobs count=%s", len(jobs))
                for job in jobs:
                    fal_meta = (job.meta or {}).get("fal") if isinstance(job.meta, dict) else None
                    request_id = (getattr(job, "request_id", None) or (fal_meta.get("requestId") if isinstance(fal_meta, dict) else None))
                    # endpoint/model_id для статуса всегда берём из Model.name
                    model_id = None
                    if job.model_id:
                        try:
                            m = db.query(Model).filter(Model.id == job.model_id).first()
                            if m and isinstance(m.name, str) and m.name:
                                parts = m.name.split("/")
                                model_id = m.name
                        except Exception:
                            logger.exception("fal.poll: failed to derive model_id from model.name for job_id=%s", job.id)
                    if not request_id:
                        continue

                    try:
                        logger.info(
                            "fal.poll: job begin job_id=%s status=%s request_id=%s model_id=%s",
                            job.id,
                            job.status,
                            request_id,
                            model_id,
                        )
                        st = get_request_status(request_id, logs=False, model_id=model_id)
                        st_status = (st.get("status") or "").upper()
                        logger.info(
                            "fal.poll: status job_id=%s request_id=%s status=%s",
                            job.id,
                            request_id,
                            st_status,
                        )
                        if st_status == "IN_PROGRESS":
                            if job.status != "processing":
                                job.status = "processing"
                                db.commit()
                                db.refresh(job)
                                logger.info("fal.poll: job moved to processing job_id=%s", job.id)
                            continue
                        if st_status == "COMPLETED":
                            try:
                                resp = get_request_response(request_id, model_id=model_id)
                            except Exception:
                                logger.exception("fal.poll: get_request_response failed")
                                resp = {}
                            media_url = _pick_media_url(st, resp or {})
                            if not media_url:
                                # Нет URL — считаем ошибкой
                                job.status = "failed"
                                db.commit()
                                db.refresh(job)
                                logger.warning("fal.poll: media url not found job_id=%s request_id=%s", job.id, request_id)
                                notify_job_event(
                                    event="job.failed",
                                    job_id=str(job.id),
                                    user_id=str(job.user_id) if job.user_id else None,
                                    status="failed",
                                    service_type=None,
                                    message="media url not found",
                                )
                                continue

                            # Скачиваем и кладем в S3
                            media_bytes = fetch_bytes(media_url, timeout=180)
                            logger.info(
                                "fal.poll: fetched media bytes job_id=%s bytes=%s url=%s",
                                job.id,
                                len(media_bytes) if isinstance(media_bytes, (bytes, bytearray)) else None,
                                media_url,
                            )

                            # Определяем тип результата по модели (format_to)
                            fmt_to = None
                            try:
                                if job.model_id:
                                    m = db.query(Model).filter(Model.id == job.model_id).first()
                                    fmt_to = (m.format_to or "").strip().lower() if m and m.format_to else None
                            except Exception:
                                logger.exception("fal.poll: failed to load model for job_id=%s", job.id)
                            if fmt_to == "image":
                                lower_url = (media_url or "").lower()
                                if lower_url.endswith((".jpg", ".jpeg")):
                                    ext = ".jpg"
                                    content_type = "image/jpeg"
                                elif lower_url.endswith(".png"):
                                    ext = ".png"
                                    content_type = "image/png"
                                else:
                                    ext = ".png"
                                    content_type = "image/png"
                                key = s3_key_for_video(job.anon_user_id or "user", job.order_id or str(job.id), 0, ext)
                                upload_bytes(settings.s3_bucket_name or "", key, media_bytes, content_type=content_type)
                            else:
                                key = s3_key_for_video(job.anon_user_id or "user", job.order_id or str(job.id), 0, ".mp4")
                                upload_bytes(settings.s3_bucket_name or "", key, media_bytes, content_type="video/mp4")
                            logger.info(
                                "fal.poll: uploaded to s3 bucket=%s key=%s",
                                settings.s3_bucket_name,
                                key,
                            )
                            public_url, _ = get_file_url_with_expiry(settings.s3_bucket_name or "", key)
                            job.result_url = public_url
                            job.status = "done"
                            db.commit()
                            db.refresh(job)
                            logger.info(
                                "fal.poll: job completed job_id=%s result_url=%s",
                                job.id,
                                public_url,
                            )

                            # Канал уведомления:
                            # - для задач с generation_source="site" и наличием email — отправляем письмо с ссылкой
                            # - иначе — уведомляем Telegram-бот
                            try:
                                gen_src = (getattr(job, "generation_source", None) or "").strip().lower()
                            except Exception:
                                gen_src = None
                            if gen_src == "site" and job.email:
                                try:
                                    send_email_with_links(recipient_email=job.email, links=[public_url], job_id=str(job.id))
                                    logger.info("fal.poll: email with result sent to %s for job_id=%s", job.email, job.id)
                                except Exception:
                                    logger.exception("fal.poll: failed to send result email job_id=%s", job.id)
                            else:
                                notify_job_event(
                                    event="job.completed",
                                    job_id=str(job.id),
                                    user_id=str(job.user_id) if job.user_id else None,
                                    status="done",
                                    service_type=None,
                                    result_url=public_url,
                                )
                            continue
                        if st_status in ("FAILED", "CANCELLED", "ERROR"):
                            job.status = "failed"
                            db.commit()
                            db.refresh(job)
                            logger.warning(
                                "fal.poll: job failed job_id=%s request_id=%s status=%s",
                                job.id,
                                request_id,
                                st_status,
                            )
                            notify_job_event(
                                event="job.failed",
                                job_id=str(job.id),
                                user_id=str(job.user_id) if job.user_id else None,
                                status="failed",
                                service_type=None,
                            )
                            continue
                    except Exception:
                        logger.exception("fal.poll: error processing job_id=%s", job.id)
                        # не меняем статус на ошибку сразу, пробуем в следующий цикл
                        continue
            finally:
                db.close()
        except Exception:
            logger.exception("fal.poll: unexpected loop error")
            # защита от tight loop — продолжим через интервал
            continue
        finally:
            logger.info("fal.poll: tick end")
            time.sleep(interval_seconds)



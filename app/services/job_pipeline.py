from __future__ import annotations

import logging
import os
import uuid

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.db.models import Job
from app.services.yandex_ocr_service import get_ocr_service
from app.services.yandex_gpt_service import get_gpt_service

logger = logging.getLogger(__name__)


def _load_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def process_job_pipeline(job_id: str, temp_path: str, content_type: str | None = None) -> None:
    db: Session = SessionLocal()
    job_uuid = None
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        logger.error("job_pipeline.invalid_job_id", job_id=job_id)
        return
    try:
        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            logger.warning("job_pipeline.job_missing", job_id=job_id)
            return
        logger.info("job_pipeline.start", job_id=job_id)
        job.status = "processing"
        db.commit()

        content = _load_file(temp_path)

        # OCR step
        ocr_service = get_ocr_service()
        detected_text, ocr_meta = ocr_service.recognize(content, mime_type=content_type)
        job.detected_text = detected_text
        job.ocr_operation_id = ocr_meta.get("operationId")
        job.ocr_status = "done"
        meta = dict(job.pipeline_meta or {})
        meta["ocr"] = ocr_meta
        job.pipeline_meta = meta
        db.commit()

        # GPT step
        gpt_service = get_gpt_service()
        generated_text, gpt_meta = gpt_service.generate(detected_text)
        job.generated_text = generated_text
        job.gpt_response_id = gpt_meta.get("responseId")
        meta = dict(job.pipeline_meta or {})
        meta["ocr"] = ocr_meta
        meta["gpt"] = gpt_meta
        job.pipeline_meta = meta
        job.status = "done"
        job.tokens_consumed = job.tokens_reserved
        job.is_ok = True
        db.commit()
        logger.info("job_pipeline.done", job_id=job_id)
    except Exception as exc:
        logger.exception("job_pipeline.failed", job_id=job_id)
        failed_job = db.query(Job).filter(Job.id == job_uuid).first()
        if failed_job:
            failed_job.status = "failed"
            failed_job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            logger.warning("job_pipeline.cleanup_failed", temp_path=temp_path)



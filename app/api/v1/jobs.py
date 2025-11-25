from __future__ import annotations

import os
import uuid
from decimal import Decimal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.db.models import Job, User
from app.core.config import settings
from app.services.file_utils import save_upload_to_temp
from app.services.job_pipeline import process_job_pipeline
from app.services.s3 import upload_bytes
from app.services.user_profile import avatar_id_for_ip, username_for_ip

router = APIRouter(prefix="/job", tags=["Job"])

logger = logging.getLogger(__name__)


def _to_decimal(val: Decimal | float | int | None) -> Decimal:
    if isinstance(val, Decimal):
        return val
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _serialize_job(job: Job, user: User | None = None) -> dict:
    data = {
        "id": str(job.id),
        "userId": str(job.user_id) if job.user_id else None,
        "status": str(job.status) if job.status is not None else None,
        "tokensReserved": float(job.tokens_reserved or 0),
        "tokensConsumed": float(job.tokens_consumed or 0),
        "inputS3Url": job.input_s3_url,
        "detectedText": job.detected_text,
        "generatedText": job.generated_text,
        "errorMessage": job.error_message,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
    }
    if user:
        data["user"] = {
            "id": str(user.id),
            "username": user.username,
            "avatarId": user.avatar_id,
            "isAuthorized": bool(user.is_authorized),
        }
    return data


def _find_or_create_user_by_ip(db: Session, ip: str) -> User:
    user = db.query(User).filter(User.ip == ip).first()
    if user:
        return user
    user = User(
        id=uuid.uuid4(),
        ip=ip,
        username=username_for_ip(ip),
        avatar_id=avatar_id_for_ip(ip),
        anon_user_id=str(uuid.uuid4()),
        balance_tokens=Decimal("5"),
        tokens_used_as_anon=0,
        is_authorized=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _resolve_user(db: Session, user_id: str | None, ip: str | None) -> User:
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    if ip:
        return _find_or_create_user_by_ip(db, ip)
    raise HTTPException(status_code=400, detail="Either user_id or x-user-ip header is required")


def _ensure_token_balance(user: User) -> None:
    tokens_left = _to_decimal(user.balance_tokens)
    if tokens_left <= 0:
        raise HTTPException(status_code=402, detail="Not enough tokens")
    if not user.is_authorized and (user.tokens_used_as_anon or 0) >= 2:
        raise HTTPException(status_code=403, detail="Anonymous quota exceeded")


def _debit_token(user: User) -> None:
    user.balance_tokens = _to_decimal(user.balance_tokens) - Decimal("1")
    if user.balance_tokens < 0:
        user.balance_tokens = Decimal("0")
    if not user.is_authorized:
        user.tokens_used_as_anon = (user.tokens_used_as_anon or 0) + 1


@router.post("")
async def create_job(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    userId: str | None = Form(default=None, alias="userId"),
    user_id_form: str | None = Form(default=None, alias="user_id"),
    db: Session = Depends(get_db),
    x_user_ip: str | None = Header(default=None, alias="x-user-ip"),
) -> dict:
    if not settings.s3_bucket_name:
        raise HTTPException(status_code=500, detail="S3 is not configured")
    user_identifier = userId or user_id_form
    ip = (x_user_ip or "").strip() or None

    temp_path = await save_upload_to_temp(image)
    try:
        user = _resolve_user(db, user_identifier, ip)
        _ensure_token_balance(user)

        with open(temp_path, "rb") as f:
            content = f.read()

        job_id = uuid.uuid4()
        filename = image.filename or "image"
        key = f"jobs/{user.id}/{job_id}/{filename}"
        s3_url = upload_bytes(key, content, image.content_type)

        job = Job(
            id=job_id,
            user_id=user.id,
            anon_user_id=user.anon_user_id,
            status="queued",
            tokens_reserved=Decimal("1"),
            input_s3_url=s3_url,
            input_mime_type=image.content_type,
        )
        db.add(job)

        _debit_token(user)
        db.commit()
        db.refresh(job)

        background_tasks.add_task(process_job_pipeline, str(job.id), temp_path, image.content_type)

        return {
            "jobId": str(job.id),
            "status": job.status,
            "tokensLeft": float(user.balance_tokens or 0),
        }
    except HTTPException:
        db.rollback()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception:
        db.rollback()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.exception("create_job_failed")
        raise


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    user = db.query(User).filter(User.id == job.user_id).first() if job.user_id else None
    return _serialize_job(job, user)

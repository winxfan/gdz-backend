from __future__ import annotations

import uuid
from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Data as DataModel
from app.core.config import settings
from app.services.s3 import get_s3_client, upload_bytes


router = APIRouter(prefix="/data", tags=["Data"]) 


def _serialize_data(d: DataModel) -> dict:
    return {
        "id": str(d.id),
        "type": d.type,
        "s3Url": d.s3_url,
        "publicS3Url": d.public_s3_url,
        "expiredIn": int(d.expired_in or 0),
        "createdAt": d.created_at.isoformat() if d.created_at else None,
    }


@router.post("")
async def upload_multipart(
    type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not settings.s3_bucket_name:
        raise HTTPException(status_code=500, detail="S3 is not configured")
    key = f"uploads/{uuid.uuid4()}/{file.filename}"
    content = await file.read()
    s3_url = upload_bytes(key, content, file.content_type)

    data = DataModel(id=uuid.uuid4(), type=type, s3_url=s3_url)
    db.add(data)
    db.commit()
    db.refresh(data)
    return _serialize_data(data)


@router.post("/presign")
def presign(type: str, fileName: str, contentType: str, db: Session = Depends(get_db)) -> dict:
    if not settings.s3_bucket_name:
        raise HTTPException(status_code=500, detail="S3 is not configured")
    data = DataModel(id=uuid.uuid4(), type=type)
    db.add(data)
    db.commit()
    db.refresh(data)

    s3 = get_s3_client()
    key = f"uploads/{data.id}/{fileName}"
    expires = 3600
    presign = s3.generate_presigned_post(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Fields={"Content-Type": contentType},
        Conditions=[["starts-with", "$Content-Type", ""], ["content-length-range", 0, 50 * 1024 * 1024]],
        ExpiresIn=expires,
    )
    # временно сохраняем ожидаемый ключ и срок
    data.s3_url = f"s3://{settings.s3_bucket_name}/{key}"
    data.expired_in = expires
    db.commit()

    return {
        "dataId": str(data.id),
        "uploadUrl": presign.get("url"),
        "fields": presign.get("fields"),
        "expiresInSeconds": expires,
    }


@router.post("/{data_id}/confirm")
def confirm_upload(data_id: str, db: Session = Depends(get_db)) -> dict:
    data = db.query(DataModel).filter(DataModel.id == data_id).first()
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    return _serialize_data(data)





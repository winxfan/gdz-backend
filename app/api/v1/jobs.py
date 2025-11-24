from decimal import Decimal, ROUND_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.services.fal import submit_generation
from app.db.models import Job, User, Model
from app.core.config import settings
from app.services.yookassa_service import create_payment as create_yookassa_payment
from app.services.email_service import send_payment_request_email
 

router = APIRouter(prefix="/jobs", tags=["Jobs"]) 

logger = logging.getLogger(__name__)


def _serialize_job(job: Job) -> dict:
    return {
        "id": str(job.id),
        "userId": str(job.user_id) if job.user_id else None,
        "modelId": str(job.model_id) if job.model_id else None,
        "orderId": job.order_id,
        "trafficType": str(job.traffic_type) if job.traffic_type is not None else None,
        "status": str(job.status) if job.status is not None else None,
        "priceRub": float(job.price_rub or 0),
        "tokensReserved": float(job.tokens_reserved or 0),
        "tokensConsumed": float(job.tokens_consumed or 0),
        "input": job.input,
        "output": job.output,
        "resultUrl": job.result_url,
        "meta": job.meta,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("")
def create_job(payload: dict, db: Session = Depends(get_db)) -> dict:
    // todo: implement
    resp = _serialize_job(job)
    if payment_url:
        resp["paymentUrl"] = payment_url
    return resp


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    logger.debug("get_job: job_id=%s", job_id)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


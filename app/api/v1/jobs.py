from decimal import Decimal, ROUND_UP
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.db.models import Job, User
from app.core.config import settings
from app.services.yookassa_service import create_payment as create_yookassa_payment
 

router = APIRouter(prefix="/jobs", tags=["Jobs"]) 

logger = logging.getLogger(__name__)


def _serialize_job(job: Job) -> dict:
    return {
        "id": str(job.id),
        "userId": str(job.user_id) if job.user_id else None,
        "orderId": job.order_id,
        "status": str(job.status) if job.status is not None else None,
        "tokensReserved": float(job.tokens_reserved or 0),
        "tokensConsumed": float(job.tokens_consumed or 0),
        "output": job.output,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("")
def create_job(payload: dict, db: Session = Depends(get_db)) -> dict:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    logger.debug("get_job: job_id=%s", job_id)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


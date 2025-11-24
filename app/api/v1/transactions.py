from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"]) 


def _serialize_txn(t: Transaction) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "userId": str(t.user_id) if t.user_id else None,
        "jobId": str(t.job_id) if t.job_id else None,
        "type": str(t.type) if t.type is not None else None,
        "provider": str(t.provider) if t.provider is not None else None,
        "status": str(t.status) if t.status is not None else None,
        "amountRub": float(t.amount_rub or 0),
        "tokensDelta": float(t.tokens_delta or 0),
        "currency": t.currency,
        "plan": t.plan,
        "reference": t.reference,
        "meta": t.meta,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("")
def list_transactions(userId: str, db: Session = Depends(get_db)) -> list[dict]:
    items = (
        db.query(Transaction)
        .filter(Transaction.user_id == userId)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return [_serialize_txn(t) for t in items]


# Временная заглушка вне спецификации (может быть удалена)
@router.post("/checkout")
def checkout(amount_rub: float) -> dict:
    return {"checkoutUrl": "https://yookassa.example/checkout/stub"}


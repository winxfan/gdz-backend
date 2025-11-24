from __future__ import annotations

from decimal import Decimal
from fastapi import APIRouter

router = APIRouter(prefix="/tariffs", tags=["Tariffs"]) 


@router.get("")
def list_tariffs() -> list[dict]:
    return [
        {
            "id": "basic",
            "name": "basic",
            "title": "Базовый",
            "monthlyTokens": 300,
            "costRub": 299.0,
            "currency": "RUB",
        },
        {
            "id": "pro",
            "name": "pro",
            "title": "Про",
            "monthlyTokens": 1200,
            "costRub": 899.0,
            "currency": "RUB",
        },
    ]





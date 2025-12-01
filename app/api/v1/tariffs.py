from __future__ import annotations

from fastapi import APIRouter

from app.services.tariff_catalog import list_tariffs as list_available_tariffs

router = APIRouter(prefix="/tariffs", tags=["Tariffs"]) 


@router.get("")
def list_tariffs() -> list[dict]:
    return list_available_tariffs()





from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, TypedDict, List


class TariffInfo(TypedDict):
    id: str
    title: str
    tokens: int
    price_rub: Decimal
    currency: str


_TARIFFS: Dict[str, TariffInfo] = {
    "1": {
        "id": "1",
        "title": "10 токенов",
        "tokens": 10,
        "price_rub": Decimal("76"),
        "currency": "RUB",
    },
    "2": {
        "id": "2",
        "title": "31 токен",
        "tokens": 31,
        "price_rub": Decimal("174"),
        "currency": "RUB",
    },
    "3": {
        "id": "3",
        "title": "150 токенов",
        "tokens": 150,
        "price_rub": Decimal("701"),
        "currency": "RUB",
    },
}


def list_tariffs() -> List[Dict[str, Any]]:
    """Возвращает тарифы в формате пригодном для JSON."""
    items: List[Dict[str, Any]] = []
    for tariff in _TARIFFS.values():
        items.append(
            {
                "id": tariff["id"],
                "title": tariff["title"],
                "tokens": tariff["tokens"],
                "costRub": float(tariff["price_rub"]),
                "currency": tariff["currency"],
            }
        )
    return items


def get_tariff(tariff_id: str) -> TariffInfo | None:
    return _TARIFFS.get(str(tariff_id))


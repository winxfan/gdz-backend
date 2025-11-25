from __future__ import annotations

from typing import Sequence

ANIMALS: Sequence[str] = ["лиса", "панда", "енот", "сова", "пингвин"]
ADJECTIVES: Sequence[str] = [
    "Могучий",
    "Игривый",
    "Смелый",
    "Ловкий",
    "Хитрый",
    "Доблестный",
    "Лукавый",
    "Бархатный",
    "Серебряный",
    "Шустрый",
    "Бесстрашный",
    "Космический",
    "Отважный",
    "Мистический",
    "Солнечный",
    "Яркий",
    "Легендарный",
    "Вихревой",
    "Лучезарный",
    "Зоркий",
    "Внушительный",
    "Бурный",
    "Грозовой",
    "Ласковый",
]


def _hash(value: str) -> int:
    h = 0
    for char in value:
        h = (h * 31 + ord(char)) & 0xFFFFFFFF
    return h


def avatar_id_for_ip(ip: str) -> int:
    if not ip:
        return 1
    return (_hash(ip) % len(ANIMALS)) + 1


def username_for_ip(ip: str) -> str:
    if not ip:
        return "Гость"
    h = _hash(ip)
    adjective = ADJECTIVES[h % len(ADJECTIVES)]
    animal = ANIMALS[h % len(ANIMALS)]
    return f"{adjective} {animal}"



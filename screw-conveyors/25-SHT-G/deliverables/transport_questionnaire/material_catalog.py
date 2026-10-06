"""Small traceable bulk-material reference catalog used by the questionnaire."""

from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("material_cards.json")


def cards() -> dict[str, dict]:
    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["cards"]
    return {row["code"]: row for row in rows}


def get_card(code: str) -> dict:
    card = cards().get(str(code).strip())
    if card is None:
        raise ValueError(f"Карточка материала {code!r} отсутствует в справочнике программы")
    return card

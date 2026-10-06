"""Purchased-item selection and draft specification export.

The bundled catalog is a transcription of the supplied assembly BOM. It is not a
supplier database and its quantities are only the baseline for that assembly.
"""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("purchased_catalog.json")


def baseline_items() -> list[dict]:
    return deepcopy(json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["items"])


def validate_items(items: list[dict]) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError("Перечень покупных изделий должен быть списком")
    clean = []
    ids = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Строка {index}: неверный формат")
        item_id = str(item.get("id", "")).strip()
        name = str(item.get("designation", "")).strip()
        category = str(item.get("category", "")).strip()
        if not item_id or item_id in ids or not name or not category:
            raise ValueError(f"Строка {index}: укажите уникальный код, группу и обозначение")
        ids.add(item_id)
        try:
            quantity = int(str(item.get("quantity", "")).strip())
        except ValueError:
            raise ValueError(f"Строка {index}: количество должно быть целым") from None
        if quantity < 1:
            raise ValueError(f"Строка {index}: количество должно быть не менее 1")
        selected = item.get("selected", False)
        if not isinstance(selected, bool):
            raise ValueError(f"Строка {index}: поле выбора должно быть логическим")
        clean.append({
            "id": item_id, "category": category, "designation": name,
            "quantity": quantity, "selected": selected,
            "note": str(item.get("note", "")).strip(),
            "source": str(item.get("source", "")).strip(),
            "source_position": item.get("source_position"),
        })
    return clean


def selected_items(items: list[dict]) -> list[dict]:
    return [item for item in validate_items(items) if item["selected"]]


def cad_compatibility_warnings(items: list[dict]) -> list[str]:
    """Flag catalog choices that disagree with the supplied native CAD geometry."""
    selected = selected_items(items)
    bearings = [item for item in selected if item["category"] == "Подшипники"]
    warnings = []
    if len(bearings) != 1 or bearings[0]["designation"] != "Подшипник NSK 7213BEA" or bearings[0]["quantity"] != 4:
        warnings.append("Выбранные подшипники отличаются от 4 × NSK 7213BEA в исходной CAD-сборке; "
                        "нужно пересчитать опоры и проверить посадки вала, обойм и крепёж")
    return warnings


def write_specification(items: list[dict], path: str | Path) -> Path:
    """Write a draft purchased-items section, retaining separate BOM positions."""
    path = Path(path)
    selected = selected_items(items)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["Позиция", "Раздел", "Обозначение", "Количество", "Примечание", "Источник"])
        for number, item in enumerate(selected, 1):
            writer.writerow([number, item["category"], item["designation"],
                             item["quantity"], item["note"], item["source"]])
    return path

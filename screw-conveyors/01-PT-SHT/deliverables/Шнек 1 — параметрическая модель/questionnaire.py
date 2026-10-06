"""Persist operating conditions supplied through the project questionnaire."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
PATH = BASE / "operation_questionnaire.json"
FIELDS = ("starts_per_hour", "run_minutes", "loaded_start", "mixture_density_kg_m3")
DEFAULT = {key: None for key in FIELDS}


def read() -> dict:
    if not PATH.exists():
        return DEFAULT.copy()
    saved = json.loads(PATH.read_text(encoding="utf-8"))
    return {key: saved.get(key) for key in FIELDS}


def _positive_number(value, name: str, *, integer: bool = False, maximum: float | None = None):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name}: требуется положительное число")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: требуется положительное число") from exc
    if not math.isfinite(number) or number <= 0 or (maximum is not None and number > maximum):
        raise ValueError(f"{name}: значение вне допустимого диапазона")
    if integer and not number.is_integer():
        raise ValueError(f"{name}: требуется целое число")
    return int(number) if integer else number


def validate(raw: dict) -> dict:
    if not isinstance(raw, dict) or set(raw) - set(FIELDS):
        raise ValueError("Неизвестные поля опроса")
    result = {
        "starts_per_hour": _positive_number(raw.get("starts_per_hour"), "Число пусков в час", integer=True),
        "run_minutes": _positive_number(raw.get("run_minutes"), "Длительность включения", maximum=60),
        "mixture_density_kg_m3": _positive_number(raw.get("mixture_density_kg_m3"), "Плотность смеси"),
    }
    loaded = raw.get("loaded_start")
    if loaded not in (None, "yes", "no"):
        raise ValueError("Пуск с заполненным шнеком: выберите да, нет или не определено")
    result["loaded_start"] = loaded
    if result["starts_per_hour"] and result["run_minutes"]:
        if result["starts_per_hour"] * result["run_minutes"] > 60:
            raise ValueError("Число пусков × длительность одного включения превышает 60 мин/ч")
    return result


def save(raw: dict) -> dict:
    data = validate(raw)
    temporary = PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, PATH)
    return data

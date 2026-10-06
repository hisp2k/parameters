# -*- coding: utf-8 -*-
"""
Каталог приводных комплектующих (раздел 11 задания).

СТАТУС: реального каталога поставщика приводов Тех-Аэро нет (см.
calculator/README_RU.md, раздел 7, пункт 2 — прямой открытый вопрос
пользователю). `EXAMPLE_MOTOR_CATALOG`/`EXAMPLE_GEARBOX_CATALOG` ниже —
ИЛЛЮСТРАТИВНЫЕ данные (типовые для общепромышленных асинхронных
электродвигателей и червячных/цилиндрических редукторов, порядок величин
реалистичный, но НЕ привязаны к конкретному производителю/прайс-листу) —
использовать их для реального выпуска ЗАПРЕЩЕНО, это прямо проверяется
через `CatalogEntry.verified_source`. Раздел 11 прямо требует: "Если
каталог отсутствует, реализуй его импорт и подбор по заданным
характеристикам, а результатом выдавай требования к комплектующим" — именно
поэтому есть `load_catalog_from_csv()`: как только появится реальный CSV
от поставщика, его можно подключить без изменения кода подбора
(core/drive_selection.py).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MotorCatalogEntry:
    designation: str
    power_kw: float
    rated_speed_rpm: float                 # об/мин при 50 Гц
    rated_torque_nm: float
    max_overload_torque_factor: float       # во сколько раз кратковременно можно превысить номинальный момент
    duty_class: str                         # "S1" (продолжительный) и т.п.
    mount_type: str                         # напр. "IM B5", "IM B14"
    rated_current_a: float
    voltage_v: str
    has_independent_cooling_fan: bool       # нужен для длительной работы на пониженных оборотах через ПЧ
    verified_source: str = "иллюстративные данные — НЕ каталог поставщика"


@dataclass
class GearboxCatalogEntry:
    designation: str
    ratio: float
    max_output_torque_nm: float
    max_input_power_kw: float
    mount_type: str
    verified_source: str = "иллюстративные данные — НЕ каталог поставщика"


# Иллюстративный ряд — ПОРЯДОК величин типовой для общепромышленных АИР/АИС
# 4-полюсных двигателей (номинальные обороты ~1430-1460 об/мин при 50 Гц),
# но НЕ выписан из реального прайс-листа. verified_source помечает это явно
# на каждой записи, а не только в docstring файла.
EXAMPLE_MOTOR_CATALOG: list[MotorCatalogEntry] = [
    MotorCatalogEntry("АИР71B4 (илл.)", 0.75, 1370, 5.2, 2.2, "S1", "IM B5", 2.1, "380В", False),
    MotorCatalogEntry("АИР80A4 (илл.)", 1.1, 1390, 7.6, 2.2, "S1", "IM B5", 2.7, "380В", False),
    MotorCatalogEntry("АИР90L4 (илл.)", 2.2, 1400, 15.0, 2.2, "S1", "IM B5", 5.0, "380В", False),
    MotorCatalogEntry("АИР100S4 (илл.)", 3.0, 1410, 20.3, 2.2, "S1", "IM B5", 6.7, "380В", True),
    MotorCatalogEntry("АИР112M4 (илл.)", 5.5, 1420, 37.0, 2.2, "S1", "IM B5", 11.7, "380В", True),
    MotorCatalogEntry("АИР132S4 (илл.)", 7.5, 1440, 49.7, 2.2, "S1", "IM B5", 15.4, "380В", True),
    MotorCatalogEntry("АИР160S4 (илл.)", 15.0, 1460, 98.1, 2.0, "S1", "IM B5", 29.5, "380В", True),
]

EXAMPLE_GEARBOX_CATALOG: list[GearboxCatalogEntry] = [
    GearboxCatalogEntry("Ц2У-100 (илл.)", 10.0, 250.0, 3.0, "IM B5"),
    GearboxCatalogEntry("Ц2У-125 (илл.)", 16.0, 500.0, 5.5, "IM B5"),
    GearboxCatalogEntry("Ц2У-160 (илл.)", 20.0, 900.0, 11.0, "IM B5"),
    GearboxCatalogEntry("Ц2У-200 (илл.)", 25.0, 1600.0, 22.0, "IM B5"),
]


def load_motor_catalog_from_csv(path: Path | str) -> list[MotorCatalogEntry]:
    """
    Реальный импорт каталога (раздел 11: "реализуй его импорт... по заданным
    характеристикам"). Ожидаемые колонки перечислены в заголовке CSV; любая
    строка с нечисловым значением в числовой колонке отклоняется с понятной
    ошибкой, а не пропускается молча.
    """
    path = Path(path)
    entries: list[MotorCatalogEntry] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {
            "designation", "power_kw", "rated_speed_rpm", "rated_torque_nm",
            "max_overload_torque_factor", "duty_class", "mount_type",
            "rated_current_a", "voltage_v", "has_independent_cooling_fan",
        }
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"В CSV {path} отсутствуют обязательные колонки: {sorted(missing)}")
        for i, row in enumerate(reader, start=2):
            try:
                entries.append(MotorCatalogEntry(
                    designation=row["designation"],
                    power_kw=float(row["power_kw"]),
                    rated_speed_rpm=float(row["rated_speed_rpm"]),
                    rated_torque_nm=float(row["rated_torque_nm"]),
                    max_overload_torque_factor=float(row["max_overload_torque_factor"]),
                    duty_class=row["duty_class"],
                    mount_type=row["mount_type"],
                    rated_current_a=float(row["rated_current_a"]),
                    voltage_v=row["voltage_v"],
                    has_independent_cooling_fan=row["has_independent_cooling_fan"].strip().lower()
                    in ("1", "true", "да", "yes"),
                    verified_source=row.get("verified_source") or f"импортировано из {path.name}",
                ))
            except (KeyError, ValueError) as e:
                raise ValueError(f"{path}, строка {i}: некорректные данные ({e}).") from e
    return entries

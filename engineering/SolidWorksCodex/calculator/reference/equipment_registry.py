# -*- coding: utf-8 -*-
"""
Оборудование предприятия (раздел 16 задания).

Данные взяты как есть из сведений пользователя и ТРЕБУЮТ проверки паспортами
перед использованием для конкретной операции (раздел 16 — прямое указание).
Возможности, не перечисленные явно (например, наличие токарного станка или
станка для навивки спирали), здесь отсутствуют и НЕ должны выводиться из
названия/класса станка — раздел 16: "Не выводи из названия станка неизвестные
возможности".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Equipment:
    equipment_id: str
    name: str
    stated_capabilities: dict = field(default_factory=dict)
    notes: str = ""
    verified_by_datasheet: bool = False


EQUIPMENT_REGISTRY: dict[str, Equipment] = {
    "laser_sheet_tube": Equipment(
        equipment_id="laser_sheet_tube",
        name="Лазер лист/труба",
        stated_capabilities={
            "лист_мм": "1500x6000",
            "мощность_кВт": 3,
            "труба_круглая_max_мм": 220,
            "труба_квадратная_max_мм": 150,
            "длина_max_мм": 6000,
        },
        notes="Цветные металлы на этом лазере не резать.",
    ),
    "bandsaw_als4040d": Equipment(
        equipment_id="bandsaw_als4040d",
        name="Ленточнопильный ALS4040D",
        stated_capabilities={"круг_max_мм": 400, "прямоугольник_max_мм": "400x400"},
    ),
    "vmc_850p": Equipment(
        equipment_id="vmc_850p",
        name="VMC-850P",
        stated_capabilities={
            "стол_мм": "1000x500",
            "нагрузка_max_кг": 500,
            "об_мин_max": 8000,
            "инструмент": "BT40",
            "оси": "заявлено 4",
        },
        notes="Четырёхосевое исполнение заявлено пользователем — не подтверждено паспортом.",
    ),
    "wirecut_dk7750": Equipment(
        equipment_id="wirecut_dk7750",
        name="Проволочно-вырезной DK7750",
        stated_capabilities={
            "перемещения_мм": "550x650",
            "толщина_max_мм": 500,
            "масса_max_кг": 600,
        },
    ),
    "drill_stalex_shd40": Equipment(
        equipment_id="drill_stalex_shd40",
        name="Сверлильный STALEX SHD-40 PF Pro",
        stated_capabilities={},
        notes="Характеристики не переданы — требуется паспорт.",
    ),
    "deburr_sghd1300l": Equipment(
        equipment_id="deburr_sghd1300l",
        name="Зачистной SGHD-1300-L",
        stated_capabilities={},
        notes="Характеристики не переданы — требуется паспорт.",
    ),
    "belt_grinder_heden_sf150v": Equipment(
        equipment_id="belt_grinder_heden_sf150v",
        name="Ленточные шлифовальные Heden SF-150V",
        stated_capabilities={"количество": 2},
    ),
    "electrochem_cweld_x10": Equipment(
        equipment_id="electrochem_cweld_x10",
        name="Электрохимическая очистка C-WELD X10",
        stated_capabilities={},
    ),
    "bsm_270_saf": Equipment(
        equipment_id="bsm_270_saf",
        name="BSM-270 SAF",
        stated_capabilities={},
        notes="Характеристики не переданы пользователем — уточнить.",
    ),
    "press_nordberg_n36150e": Equipment(
        equipment_id="press_nordberg_n36150e",
        name="Пресс NORDBERG N36150E",
        stated_capabilities={"усилие_т": 150, "ход_мм": 350},
    ),
    "manual_plasma": Equipment(
        equipment_id="manual_plasma",
        name="Ручная плазма",
        stated_capabilities={"ток_А": 170, "резка_углеродистой_стали_max_мм": 35},
        notes="Заявленная максимальная толщина резки — со слов пользователя, не из паспорта.",
    ),
    "welding_tables": Equipment(
        equipment_id="welding_tables",
        name="Сварочные столы",
        stated_capabilities={"размер_мм": "2400x7000", "количество": 2},
    ),
}


# Явно НЕ подтверждено (раздел 16): токарная обработка, листогибка, навивка
# спирали. Если технология детали требует одну из этих операций, она должна
# получить статус "требует уточнения" — см. technology-модуль (не реализован
# в этом этапе) и release_gate.py.
UNCONFIRMED_CAPABILITIES = [
    "токарная обработка",
    "листогибочная операция (гибка листа прессом)",
    "навивка/формование спирали шнека",
]


def check_operation_feasible(equipment_id: str, requirement: str) -> str:
    """
    Всегда возвращает статус, требующий подтверждения человеком — раздел 16
    прямо запрещает выводить возможности из названия станка. Эта функция —
    место, куда технология детали должна обращаться, а не источник
    автоматического да/нет.
    """
    eq = EQUIPMENT_REGISTRY.get(equipment_id)
    if eq is None:
        return f"Оборудование {equipment_id!r} не найдено в реестре."
    if not eq.verified_by_datasheet:
        return (
            f"{eq.name}: возможность выполнить операцию {requirement!r} требует "
            "проверки паспортом станка, оснасткой, закреплением, мощностью и "
            "достижимой точностью — не подтверждено автоматически."
        )
    return f"{eq.name}: см. проверенные данные паспорта для {requirement!r}."

# -*- coding: utf-8 -*-
"""
Отдельный опросный лист для валового ТРУБЧАТОГО шнека (Issue #3,
продолжение 17.09.2026, этап 2).

`core/questionnaire.py::QuestionnaireInput` — это ВХОД ИНЖЕНЕРНОГО ЯДРА
(типизированные dataclass-поля, нужные коду). Опросный лист — другая вещь:
документ для человека и для передачи заказчику/Дмитрию Александровичу, где
у КАЖДОГО параметра должны быть видны value/unit/source/status/author/date
одновременно — это уже есть в этом репозитории как `core/parameters.py::
Parameter`/`ParameterSet` (раздел 19: "любое значение, которое течёт между
модулями... должно быть обёрнуто в Parameter"), поэтому лист строится на
этой существующей модели, а не на новом типе.

Часть полей, которые требует лист (материал корпуса/винта/вала, наличие
подвесных опор, требования по износу/герметичности), в `QuestionnaireInput`
пока НЕТ — это специфика конструкции трубного шнека, инженерное ядро их
ещё не использует. Они собраны в `TubeConstructionInput` — отдельный,
явно необязательный набор, который лист принимает как есть (MISSING, если
не передан) и не пытается вывести откуда-то ещё.

Лист сам по себе НЕ проверяет полноту (это по-прежнему делает
`validate_questionnaire()`/`compute_tube_engineering_core()`), он только
честно ОТОБРАЖАЕТ, что известно, откуда и с каким статусом.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from calculator.core.parameters import ParameterSet, ParamStatus
from calculator.core.questionnaire import QuestionnaireInput


@dataclass
class TubeConstructionInput:
    """
    Раздел "Конструкция" опросного листа — поля, которых нет в
    QuestionnaireInput (инженерное ядро их пока не использует). Все
    Optional; None => на листе честно ляжет MISSING, а не подстановка.
    """

    housing_material: Optional[str] = None
    screw_material: Optional[str] = None
    shaft_material: Optional[str] = None
    has_intermediate_supports: Optional[bool] = None
    wear_requirements: Optional[str] = None
    sealing_requirements: Optional[str] = None


def _status_for(value) -> ParamStatus:
    return ParamStatus.MISSING if value is None else ParamStatus.USER_INPUT


def build_tube_questionnaire_sheet(
    q: QuestionnaireInput,
    construction: TubeConstructionInput = TubeConstructionInput(),
    *,
    author: str = "система",
    geometry_conflict_note: Optional[str] = None,
    drive_location_conflict_note: Optional[str] = None,
) -> ParameterSet:
    """
    Строит полный опросный лист (ParameterSet) по трём разделам задания:
    О продукте / Геометрия / Конструкция. `q.conveyor_kind` не проверяется
    здесь строго (лист можно построить и для наглядности по трубному виду
    из анкеты другого вида), но осмыслен в первую очередь для SHAFTED_TUBE.
    """
    sheet = ParameterSet()

    def add(name: str, value, unit: str = "", source: str = "анкета", status: Optional[ParamStatus] = None,
             note: Optional[str] = None):
        sheet.put(name, value, unit=unit, source=source,
                   status=status if status is not None else _status_for(value),
                   author=author, note=note)

    # --- О продукте ---
    add("исходное_название_среды", q.material.material_name, source="анкета/эскиз")
    add("производительность", q.productivity.value,
        unit=(q.productivity.unit.value if q.productivity.unit is not None else ""))
    add("единица_производительности", q.productivity.unit.value if q.productivity.unit is not None else None)
    add("плотность", q.material.bulk_density_kg_m3, unit="кг/м3")
    add("концентрация_твёрдой_фазы", q.optional.solids_concentration_percent, unit="%")
    add("максимальная_крупность", q.material.max_lump_size_mm, unit="мм")
    add("абразивность", q.material.abrasiveness.value if q.material.abrasiveness is not None else None)
    add("влажность", q.material.moisture_percent, unit="%")
    add("температура", q.material.temperature_c, unit="°C")
    add("коррозионность", q.optional.corrosion_requirements)
    add("запуск_под_нагрузкой", q.optional.startup_under_load)
    duty_mode_is_default = any("duty_mode" in d for d in q.profile.accepted_defaults)
    add("режим_работы", q.profile.duty_mode,
        status=ParamStatus.ASSUMED_DEFAULT if duty_mode_is_default else _status_for(q.profile.duty_mode))
    add("число_пусков_в_сутки", q.optional.starts_per_day, unit="пусков/сутки")

    # --- Геометрия ---
    add("dn_присоединения", q.geometry.connection_diameter_mm, unit="мм", source="анкета/эскиз (п.1)")
    add("длина_по_оси", q.geometry.working_length_mm, unit="мм", source="анкета/эскиз (п.3)")
    add("угол", q.geometry.incline_deg, unit="°", source="анкета/эскиз (п.2)")
    add("высота_входа", q.geometry.load_height_from_floor_mm, unit="мм", source="анкета/эскиз (п.6)")
    add("высота_выхода", q.geometry.unload_height_from_floor_mm, unit="мм", source="анкета/эскиз (п.7)")
    add("расположение_привода_текст", q.optional.drive_location_text,
        source=q.optional.drive_location_text_source or "анкета/эскиз (текст, п.5)")
    add("расположение_привода_графика", q.optional.drive_location_graphic,
        source=q.optional.drive_location_graphic_source or "анкета/эскиз (графика)")
    add("габаритные_ограничения", q.optional.dimension_limits_mm, unit="мм")
    if geometry_conflict_note:
        sheet["длина_по_оси"].note = geometry_conflict_note
        sheet["угол"].note = geometry_conflict_note
    if drive_location_conflict_note:
        sheet["расположение_привода_текст"].note = drive_location_conflict_note
        sheet["расположение_привода_графика"].note = drive_location_conflict_note

    # --- Конструкция ---
    add("материал_корпуса", construction.housing_material)
    add("материал_винта", construction.screw_material)
    add("материал_вала", construction.shaft_material)
    add("наличие_подвесных_опор", construction.has_intermediate_supports)
    add("требования_по_износу", construction.wear_requirements)
    add("требования_по_герметичности", construction.sealing_requirements)

    return sheet


PRODUCT_SECTION_FIELDS = [
    "исходное_название_среды", "производительность", "единица_производительности", "плотность",
    "концентрация_твёрдой_фазы", "максимальная_крупность", "абразивность", "влажность",
    "температура", "коррозионность", "запуск_под_нагрузкой", "режим_работы",
    "число_пусков_в_сутки",
]
GEOMETRY_SECTION_FIELDS = [
    "dn_присоединения", "длина_по_оси", "угол", "высота_входа", "высота_выхода",
    "расположение_привода_текст", "расположение_привода_графика", "габаритные_ограничения",
]
CONSTRUCTION_SECTION_FIELDS = [
    "материал_корпуса", "материал_винта", "материал_вала",
    "наличие_подвесных_опор", "требования_по_износу", "требования_по_герметичности",
]
ALL_SHEET_FIELDS = PRODUCT_SECTION_FIELDS + GEOMETRY_SECTION_FIELDS + CONSTRUCTION_SECTION_FIELDS


def missing_fields(sheet: ParameterSet) -> list[str]:
    return [name for name in ALL_SHEET_FIELDS if sheet.get(name) is not None and sheet[name].status == ParamStatus.MISSING]

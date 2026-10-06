# -*- coding: utf-8 -*-
"""
Тесты отдельного опросного листа SHAFTED_TUBE (Issue #3, продолжение
17.09.2026, этап 2) — построен на существующей модели core/parameters.py
(Parameter: value/unit/source/status/author/date), не на новом типе.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails,
)
from calculator.core.parameters import ParamStatus
from calculator.core.tube_engineering import DriveLocation
from calculator.core.tube_questionnaire_sheet import (
    build_tube_questionnaire_sheet, TubeConstructionInput, missing_fields,
    ALL_SHEET_FIELDS, PRODUCT_SECTION_FIELDS, GEOMETRY_SECTION_FIELDS, CONSTRUCTION_SECTION_FIELDS,
)


def _sketch_q() -> QuestionnaireInput:
    return QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(material_name="вода с песком"),
        productivity=ProductivityInput(),
        geometry=GeometryInput(
            mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=2515.0, incline_deg=35.0,
            connection_diameter_mm=100.0, load_height_from_floor_mm=500.0, unload_height_from_floor_mm=1500.0,
        ),
        profile=OperatingProfileInput(construction_material="Ст3"),
        optional=OptionalDetails(
            drive_location_text=DriveLocation.LOWER_END.value, drive_location_text_source="текст эскиза, п.5",
            drive_location_graphic=DriveLocation.UPPER_END.value, drive_location_graphic_source="графика эскиза",
        ),
    )


def test_sheet_has_every_field_from_the_three_sections():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    assert set(sheet.keys()) == set(ALL_SHEET_FIELDS)
    assert len(PRODUCT_SECTION_FIELDS) == 13
    assert len(GEOMETRY_SECTION_FIELDS) == 8
    assert len(CONSTRUCTION_SECTION_FIELDS) == 6


def test_every_field_has_value_unit_source_status_author_date():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    for name in ALL_SHEET_FIELDS:
        p = sheet[name]
        assert hasattr(p, "value")
        assert isinstance(p.unit, str)
        assert isinstance(p.source, str) and p.source
        assert isinstance(p.status, ParamStatus)
        assert p.author
        assert p.date


def test_known_sketch_fields_are_user_input_status():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    for name in ("dn_присоединения", "длина_по_оси", "угол", "высота_входа", "высота_выхода",
                 "исходное_название_среды", "расположение_привода_текст", "расположение_привода_графика"):
        assert sheet[name].status == ParamStatus.USER_INPUT, name
    assert sheet["dn_присоединения"].value == 100.0
    assert sheet["исходное_название_среды"].value == "вода с песком"


def test_unknown_fields_are_missing_status_not_invented():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    for name in ("плотность", "абразивность", "максимальная_крупность", "производительность"):
        p = sheet[name]
        assert p.status == ParamStatus.MISSING
        assert p.value is None


def test_construction_fields_missing_when_not_supplied():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    for name in CONSTRUCTION_SECTION_FIELDS:
        assert sheet[name].status == ParamStatus.MISSING


def test_construction_fields_filled_when_supplied():
    construction = TubeConstructionInput(
        housing_material="AISI 316", screw_material="09Г2С", shaft_material="40Х",
        has_intermediate_supports=False, wear_requirements="износостойкое покрытие спирали",
        sealing_requirements="IP65, торцевые уплотнения",
    )
    sheet = build_tube_questionnaire_sheet(_sketch_q(), construction, author="Инженер И.И.")
    assert sheet["материал_корпуса"].value == "AISI 316"
    assert sheet["материал_корпуса"].status == ParamStatus.USER_INPUT
    assert sheet["материал_корпуса"].author == "Инженер И.И."
    assert sheet["наличие_подвесных_опор"].value is False
    assert sheet["наличие_подвесных_опор"].status == ParamStatus.USER_INPUT


def test_missing_fields_helper_matches_status():
    sheet = build_tube_questionnaire_sheet(_sketch_q())
    missing = missing_fields(sheet)
    assert "плотность" in missing
    assert "dn_присоединения" not in missing


def test_conflict_notes_attach_to_relevant_fields():
    sheet = build_tube_questionnaire_sheet(
        _sketch_q(),
        geometry_conflict_note="конфликт геометрии — см. geometry_conflict",
        drive_location_conflict_note="конфликт расположения привода — см. drive_location_conflict",
    )
    assert sheet["угол"].note == "конфликт геометрии — см. geometry_conflict"
    assert sheet["длина_по_оси"].note == "конфликт геометрии — см. geometry_conflict"
    assert sheet["расположение_привода_текст"].note == "конфликт расположения привода — см. drive_location_conflict"
    assert sheet["расположение_привода_графика"].note == "конфликт расположения привода — см. drive_location_conflict"

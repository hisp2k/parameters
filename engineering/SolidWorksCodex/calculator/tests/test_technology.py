# -*- coding: utf-8 -*-
"""
Тесты технологического модуля (раздел 7 задания).

Проверяют контракт, а не "правильность" числовых норм времени (которые сам
модуль честно помечает как ориентировочные, требующие проверки нормативом
предприятия) — контракт: машинное/трудовое время/продолжительность различны
и суммируются корректно; операции без подтверждённого оборудования честно
помечены; спираль шнека имеет два разных обоснованных варианта, а не один
"придуманный" процесс; попытка выдумать несуществующую "непроверенную
возможность" отклоняется.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from calculator.core.technology import (
    OperationStep, PartProcess, AssemblyProcess, ScrewFlightMethod,
    screw_flight_process, build_default_technology_package,
)
from calculator.reference.equipment_registry import EQUIPMENT_REGISTRY, UNCONFIRMED_CAPABILITIES


def test_operation_step_with_known_unverified_equipment_requires_confirmation():
    op = OperationStep(
        name="Резка листа", equipment_id="laser_sheet_tube", requirement="резка листа",
        machine_time_min=10.0, labor_time_min=2.0, duration_min=12.0,
    )
    # Ни одна позиция реестра оборудования не verified_by_datasheet=True на этом этапе —
    # поэтому честный ответ: требует подтверждения, а не "готово к использованию".
    assert op.requires_equipment_confirmation is True
    assert "лазер" in op.feasibility_note.lower() or "лист" in op.feasibility_note.lower()


def test_operation_step_would_be_confirmed_if_datasheet_verified(monkeypatch):
    eq = EQUIPMENT_REGISTRY["laser_sheet_tube"]
    original = eq.verified_by_datasheet
    eq.verified_by_datasheet = True
    try:
        op = OperationStep(name="Резка листа", equipment_id="laser_sheet_tube", requirement="резка листа")
        assert op.requires_equipment_confirmation is False
    finally:
        eq.verified_by_datasheet = original  # не оставляем побочный эффект для других тестов


def test_operation_step_without_equipment_requires_confirmation():
    op = OperationStep(name="Операция без станка", equipment_id=None, requirement="что-то")
    assert op.requires_equipment_confirmation is True
    assert "не назначено" in op.feasibility_note


def test_operation_step_rejects_made_up_unconfirmed_capability():
    with pytest.raises(ValueError):
        OperationStep(
            name="Выдуманная операция", equipment_id=None, requirement="что-то",
            unconfirmed_capability="выдуманная возможность, которой нет в реестре",
        )


def test_operation_step_accepts_real_unconfirmed_capability():
    op = OperationStep(
        name="Гибка листа", equipment_id=None, requirement="гибка листа",
        unconfirmed_capability="листогибочная операция (гибка листа прессом)",
    )
    assert op.unconfirmed_capability in UNCONFIRMED_CAPABILITIES
    assert op.requires_equipment_confirmation is True
    assert "НЕ подтверждена" in op.feasibility_note


def test_equipment_id_not_in_registry_raises():
    with pytest.raises(ValueError):
        OperationStep(name="x", equipment_id="несуществующий_станок", requirement="что-то")


# --- разделение машинного времени / времени рабочего / продолжительности ---

def test_part_process_sums_three_time_fields_independently():
    part = PartProcess(
        bom_position="уточнить_по_BOM", component_class="тест",
        material="Ст3", blank_description="лист", dimensions_note="н/д", allowances_note="н/д",
        operations=[
            OperationStep(name="op1", equipment_id="laser_sheet_tube", requirement="резка",
                          machine_time_min=10.0, labor_time_min=2.0, duration_min=12.0),
            OperationStep(name="op2", equipment_id="welding_tables", requirement="сварка",
                          machine_time_min=0.0, labor_time_min=30.0, duration_min=35.0),
        ],
    )
    assert part.total_machine_time_min == 10.0
    assert part.total_labor_time_min == 32.0
    assert part.total_duration_min == 47.0
    # машинное время НЕ равно времени рабочего НЕ равно продолжительности — три разных числа
    assert len({part.total_machine_time_min, part.total_labor_time_min, part.total_duration_min}) == 3


def test_assembly_process_sums_welding_and_assembly_operations_together():
    asm = AssemblyProcess(
        name="Тестовый узел",
        welding_operations=[OperationStep(name="сварка", equipment_id="welding_tables", requirement="сварка",
                                           labor_time_min=20.0, duration_min=25.0)],
        assembly_operations=[OperationStep(name="сборка", equipment_id=None, requirement="сборка",
                                            labor_time_min=15.0, duration_min=20.0)],
    )
    assert asm.total_labor_time_min == 35.0
    assert asm.total_duration_min == 45.0


def test_part_process_unconfirmed_operations_lists_only_flagged_ones(monkeypatch):
    eq = EQUIPMENT_REGISTRY["laser_sheet_tube"]
    original = eq.verified_by_datasheet
    eq.verified_by_datasheet = True
    try:
        part = PartProcess(
            bom_position="уточнить_по_BOM", component_class="тест",
            material="Ст3", blank_description="лист", dimensions_note="н/д", allowances_note="н/д",
            operations=[
                OperationStep(name="op_confirmed", equipment_id="laser_sheet_tube", requirement="резка"),
                OperationStep(name="op_unconfirmed", equipment_id="welding_tables", requirement="сварка"),
            ],
        )
        names = {op.name for op in part.unconfirmed_operations}
        assert names == {"op_unconfirmed"}
    finally:
        eq.verified_by_datasheet = original


# --- спираль шнека: два разных обоснованных варианта, не один процесс -----

def test_screw_flight_process_returns_two_distinct_methods():
    methods = screw_flight_process(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    assert len(methods) == 2
    names = {m.method_name for m in methods}
    assert names == {"навивка_на_оправке", "секторная_сборка_из_плоских_заготовок"}
    for m in methods:
        assert isinstance(m, ScrewFlightMethod)
        assert m.justification.strip() != ""


def test_screw_flight_winding_method_is_not_equipment_confirmed():
    methods = screw_flight_process(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    winding = next(m for m in methods if m.method_name == "навивка_на_оправке")
    assert winding.equipment_confirmed is False
    assert winding.total_labor_time_min == 0.0  # время не оценивается — оборудование не подтверждено
    assert any(op.unconfirmed_capability == "навивка/формование спирали шнека" for op in winding.operations)


def test_screw_flight_sector_method_has_real_operations_and_more_welds_for_longer_screws():
    short = screw_flight_process(diameter_mm=200.0, step_mm=180.0, working_length_mm=1000.0)
    long = screw_flight_process(diameter_mm=200.0, step_mm=180.0, working_length_mm=5000.0)
    sector_short = next(m for m in short if m.method_name == "секторная_сборка_из_плоских_заготовок")
    sector_long = next(m for m in long if m.method_name == "секторная_сборка_из_плоских_заготовок")
    assert sector_short.equipment_confirmed is True
    assert sector_short.total_labor_time_min > 0.0
    # длиннее шнек -> больше витков -> больше сварных секторных швов -> больше труда
    assert sector_long.total_labor_time_min > sector_short.total_labor_time_min


def test_screw_flight_process_rejects_non_positive_step():
    with pytest.raises(ValueError):
        screw_flight_process(diameter_mm=200.0, step_mm=0.0, working_length_mm=3000.0)


# --- сборка полного пакета -------------------------------------------------

def test_build_default_technology_package_covers_all_strength_registry_component_classes():
    from calculator.core.strength_coverage import DEFAULT_TYPICAL_SCOPE
    pkg = build_default_technology_package(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    covered_classes = {p.component_class for p in pkg.parts}
    # "спираль шнека и её крепления" покрывается отдельно через flight_methods, не через parts;
    # "сварные соединения" — сквозной класс (сварные швы разбросаны по операциям деталей и
    # сборок, не отдельная деталь со своей заготовкой) — реально присутствует как операции
    # `_weld_op`/welding_operations во всех соответствующих частях пакета, а не как PartProcess.
    excluded = {"спираль шнека и её крепления", "сварные соединения"}
    missing = set(DEFAULT_TYPICAL_SCOPE) - covered_classes - excluded
    assert missing == set(), f"Технология не покрывает классы из реестра прочности: {missing}"

    has_weld_operation = any(
        "сварка" in op.name.lower() or "сварк" in op.requirement.lower()
        for p in pkg.parts for op in p.operations
    ) or any(a.welding_operations for a in pkg.assemblies)
    assert has_weld_operation, "класс 'сварные соединения' должен быть покрыт реальными сварочными операциями"


def test_build_default_technology_package_totals_are_positive_and_consistent():
    pkg = build_default_technology_package(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    assert pkg.total_machine_time_min > 0
    assert pkg.total_labor_time_min > 0
    assert pkg.total_duration_min > pkg.total_labor_time_min  # продолжительность включает наладку/ожидание сверх труда
    assert len(pkg.route.steps) > 0


def test_build_default_technology_package_flags_turning_and_bending_as_unconfirmed():
    pkg = build_default_technology_package(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    report = pkg.unconfirmed_operations_report()
    assert any("токарная обработка" in line for line in report)
    assert any("листогибочная операция" in line for line in report)


def test_build_default_technology_package_marks_purchased_items_with_incoming_inspection():
    pkg = build_default_technology_package(diameter_mm=200.0, step_mm=180.0, working_length_mm=3000.0)
    purchased = [p for p in pkg.parts if p.purchased_item]
    assert purchased, "ожидались покупные позиции (подшипники, муфта, крепёж)"
    for p in purchased:
        assert p.incoming_inspection_note.strip() != "", f"{p.component_class}: входной контроль не описан"

# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails, Abrasiveness,
)
from calculator.core.screw_engineering import ScrewEngineeringInput, compute_engineering_core
from calculator.core.drive_selection import select_drive, compute_requirement
from calculator.reference.drive_catalog import (
    EXAMPLE_MOTOR_CATALOG, EXAMPLE_GEARBOX_CATALOG, load_motor_catalog_from_csv,
)


def _questionnaire(**overrides) -> QuestionnaireInput:
    defaults = dict(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="песок", bulk_density_kg_m3=700.0, max_lump_size_mm=15.0,
            is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=5.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=3000.0, incline_deg=0.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    defaults.update(overrides)
    return QuestionnaireInput(**defaults)


def _engineering_result(q):
    length, angle = q.geometry.resolved_length_angle()
    return compute_engineering_core(ScrewEngineeringInput(
        productivity_value=q.productivity.value, productivity_unit=q.productivity.unit.value,
        bulk_density_kg_m3=q.material.bulk_density_kg_m3, max_lump_size_mm=q.material.max_lump_size_mm,
        is_sorted_material=q.material.is_sorted_material, abrasiveness=q.material.abrasiveness.value,
        working_length_mm=length, incline_deg=angle,
        forced_diameter_mm=q.forced_diameter_mm, forced_step_mm=q.forced_step_mm,
    ))


def test_requirement_without_catalog_returns_specs_not_a_fake_pick():
    q = _questionnaire()
    er = _engineering_result(q)
    result = select_drive(er, q)  # без каталога
    assert result.catalog_used is False
    assert result.selected_motor is None
    assert result.requirement.required_power_kw > 0
    assert result.requirement.running_torque_nm > 0
    assert any("не подключён" in w for w in result.warnings)


def test_starting_torque_higher_when_startup_under_load():
    q_normal = _questionnaire()
    q_loaded = _questionnaire(optional=OptionalDetails(startup_under_load=True))
    er = _engineering_result(q_normal)
    req_normal = compute_requirement(er, q_normal)
    req_loaded = compute_requirement(er, q_loaded)
    assert req_loaded.starting_torque_nm > req_normal.starting_torque_nm


def test_select_drive_with_example_catalog_finds_a_motor():
    q = _questionnaire()
    er = _engineering_result(q)
    result = select_drive(er, q, motors=EXAMPLE_MOTOR_CATALOG, gearboxes=EXAMPLE_GEARBOX_CATALOG)
    assert result.catalog_used is True
    assert result.selected_motor is not None
    # illustrative-catalog marking must survive into the selection, not be hidden
    assert "иллюстратив" in result.selected_motor.verified_source


def test_select_drive_checks_include_not_computable_items_honestly():
    q = _questionnaire()
    er = _engineering_result(q)
    result = select_drive(er, q, motors=EXAMPLE_MOTOR_CATALOG, gearboxes=EXAMPLE_GEARBOX_CATALOG)
    names_not_computable = {c.name for c in result.checks if not c.computable}
    assert "Разгон и момент инерции приведённых масс" in names_not_computable
    assert "Нагрузки на выходном валу редуктора (радиальные/осевые)" in names_not_computable


def test_protection_note_present_when_motor_selected():
    q = _questionnaire()
    er = _engineering_result(q)
    result = select_drive(er, q, motors=EXAMPLE_MOTOR_CATALOG, gearboxes=EXAMPLE_GEARBOX_CATALOG)
    assert result.protection_consistent is True
    assert "теплового реле" in result.protection_note


def test_no_motor_found_when_requirement_exceeds_catalog():
    q = _questionnaire(productivity=ProductivityInput(value=500.0, unit=ProductivityUnit.T_H))
    er = _engineering_result(q)
    result = select_drive(er, q, motors=EXAMPLE_MOTOR_CATALOG, gearboxes=EXAMPLE_GEARBOX_CATALOG)
    # Либо ядро само не подобрало мотор (motor_selection_ok=False), либо каталог его не покрывает —
    # в любом случае это не должно тихо вернуть маленький мотор.
    if result.selected_motor is not None:
        assert result.selected_motor.power_kw >= result.requirement.required_power_kw


def test_csv_catalog_import_rejects_missing_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("designation,power_kw\nMotorX,1.1\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        load_motor_catalog_from_csv(bad_csv)


def test_csv_catalog_import_reads_valid_file(tmp_path):
    csv_content = (
        "designation,power_kw,rated_speed_rpm,rated_torque_nm,max_overload_torque_factor,"
        "duty_class,mount_type,rated_current_a,voltage_v,has_independent_cooling_fan\n"
        "TestMotor,1.5,1400,10.2,2.2,S1,IM B5,3.5,380В,да\n"
    )
    p = tmp_path / "motors.csv"
    p.write_text(csv_content, encoding="utf-8")
    entries = load_motor_catalog_from_csv(p)
    assert len(entries) == 1
    assert entries[0].designation == "TestMotor"
    assert entries[0].has_independent_cooling_fan is True
    assert "motors.csv" in entries[0].verified_source

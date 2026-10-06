# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, Abrasiveness,
)
from calculator.core.screw_engineering import ScrewEngineeringInput, compute_engineering_core
from calculator.core.project import Project
from calculator.core.roles import Role, can, require
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.parameters import ParamStatus
from calculator.cad_adapter.section_layout import TroughSectionLayout
from calculator.documents.agreement_sheet import build_agreement_sheet_data, render_html


def _sample_project(tmp_dir: Path) -> Project:
    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="песок", bulk_density_kg_m3=1500.0, max_lump_size_mm=5.0,
            is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=10.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=4000.0, incline_deg=5.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    result = compute_engineering_core(ScrewEngineeringInput(
        productivity_value=q.productivity.value, productivity_unit=q.productivity.unit.value,
        bulk_density_kg_m3=q.material.bulk_density_kg_m3, max_lump_size_mm=q.material.max_lump_size_mm,
        is_sorted_material=q.material.is_sorted_material, abrasiveness=q.material.abrasiveness.value,
        working_length_mm=4000.0, incline_deg=5.0,
    ))
    return Project(
        project_name="Тест", customer="Тестовый заказчик", designation="test_proj",
        questionnaire=q, engineering_result=result,
    )


def test_project_save_and_load_roundtrip(tmp_path):
    project = _sample_project(tmp_path)
    path = project.save(tmp_path / "test_proj.json")
    loaded = Project.load(path)

    assert loaded.project_name == project.project_name
    assert loaded.revision == project.revision
    assert loaded.engineering_result.diameter_mm == project.engineering_result.diameter_mm
    assert loaded.questionnaire.material.material_name == "песок"
    assert loaded.questionnaire.geometry.mode == GeometryMode.AXIS_LENGTH_ANGLE
    assert loaded.strength_registry  # реестр охвата сохраняется/восстанавливается


def test_release_gate_blocks_fresh_project(tmp_path):
    project = _sample_project(tmp_path)
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    # Свежий проект без прочности/привода/КД/технологии обязан быть заблокирован —
    # это заявленное поведение раздела 20, а не забытая проверка.
    assert len(reasons) > 0
    assert any("прочност" in r.lower() for r in reasons)
    assert any("привод" in r.lower() for r in reasons)


def test_release_gate_rejects_non_head_role(tmp_path):
    project = _sample_project(tmp_path)
    reasons = evaluate_release_gate(project, requesting_role=Role.MANAGER)
    assert any("не имеет права утверждать" in r for r in reasons)


def test_roles_permission_table():
    assert can(Role.HEAD, "authorize_production_release") is True
    assert can(Role.MANAGER, "authorize_production_release") is False
    assert can(Role.ENGINEER, "review_strength_and_drive") is True
    assert can(Role.MANAGER, "review_strength_and_drive") is False


def test_roles_require_raises_permission_error():
    import pytest
    with pytest.raises(PermissionError):
        require(Role.MANAGER, "approve_rates_prices_economics")


def test_agreement_sheet_marks_preliminary_by_default(tmp_path):
    project = _sample_project(tmp_path)
    data = build_agreement_sheet_data(project)
    assert data.is_preliminary is True
    assert "ПРЕДВАРИТЕЛЬНЫЙ" in data.status_label
    html = render_html(data)
    assert "ПРЕДВАРИТЕЛЬНЫЙ ЛИСТ" in html
    assert project.project_name in html


# ---------------------------------------------------------------------------
# Project.record_trough_section_layout() — раздел 4 доп. задания
# ---------------------------------------------------------------------------

def test_record_trough_section_layout_marks_only_readback_done(tmp_path):
    project = _sample_project(tmp_path)
    fingerprint = project.compute_input_fingerprint()
    layout = TroughSectionLayout(
        ok=True,
        nominal_section_length_mm=3000.0,
        target_section_count=4,
        target_nominal_length_mm=12000.0,
        measured_section_count=4,
        measured_spacer_count=3,
        measured_joint_spacer_thickness_mm=2.0,
        measured_overall_length_estimate_mm=4 * 3000.0 + 3 * 2.0,
        connector_write_allowed=False,
        write_supported=False,
    )
    project.record_trough_section_layout(layout, recorded_by="Иванов И.И.", recorded_by_role=Role.ENGINEER)

    assert project.cad_sync.done is False
    assert project.cad_layout_readback.is_current(project.revision, fingerprint)
    assert project.cad_layout_readback.confirmed_by == "Иванов И.И."
    assert project.cad_layout_readback.confirmed_by_role == Role.ENGINEER

    p = project.parameters
    assert p["trough_target_section_count"].value == 4
    assert p["trough_nominal_section_length_mm"].value == 3000.0
    assert p["trough_target_nominal_length_mm"].value == 12000.0
    assert p["trough_measured_section_count"].value == 4
    assert p["trough_measured_section_count"].status == ParamStatus.CAD_READBACK
    assert p["trough_measured_spacer_count"].value == 3
    assert p["trough_measured_joint_spacer_thickness_mm"].value == 2.0
    assert p["trough_overall_length_estimate_mm"].value == 4 * 3000.0 + 3 * 2.0
    assert p["trough_overall_length_estimate_mm"].status == ParamStatus.CALCULATED_PRELIMINARY


def test_record_trough_section_layout_failure_invalidates_cad_sync_not_fabricated(tmp_path):
    project = _sample_project(tmp_path)
    layout = TroughSectionLayout(
        ok=False,
        nominal_section_length_mm=3000.0,
        target_section_count=4,
        target_nominal_length_mm=12000.0,
        errors=["sw_status вернул ошибку: SolidWorks не запущен"],
    )
    project.record_trough_section_layout(layout, recorded_by="Иванов И.И.", recorded_by_role=Role.ENGINEER)

    assert project.cad_sync.done is False
    assert "sw_status" in project.cad_sync.note
    # неудачное чтение не должно было выдумать значения счётчиков
    assert "trough_measured_section_count" not in project.parameters


def test_record_trough_section_layout_is_idempotent(tmp_path):
    project = _sample_project(tmp_path)
    layout = TroughSectionLayout(
        ok=True,
        nominal_section_length_mm=3000.0,
        target_section_count=4,
        target_nominal_length_mm=12000.0,
        measured_section_count=4,
        measured_spacer_count=3,
        connector_write_allowed=False,
    )
    project.record_trough_section_layout(layout, recorded_by="Иванов И.И.", recorded_by_role=Role.ENGINEER)
    params_after_first = dict(project.parameters)
    project.record_trough_section_layout(layout, recorded_by="Иванов И.И.", recorded_by_role=Role.ENGINEER)

    assert set(project.parameters.keys()) == set(params_after_first.keys())  # никаких новых/дублирующих полей
    assert project.parameters["trough_measured_section_count"].value == 4
    assert project.cad_sync.done is False
    assert project.cad_layout_readback.done is True


def test_record_trough_section_layout_roundtrips_through_save_load(tmp_path):
    project = _sample_project(tmp_path)
    layout = TroughSectionLayout(
        ok=True,
        nominal_section_length_mm=3000.0,
        target_section_count=4,
        target_nominal_length_mm=12000.0,
        measured_section_count=4,
        measured_spacer_count=3,
        connector_write_allowed=False,
    )
    project.record_trough_section_layout(layout, recorded_by="Иванов И.И.", recorded_by_role=Role.ENGINEER)
    path = project.save(tmp_path / "test_proj.json")
    loaded = Project.load(path)

    assert loaded.cad_sync.done is False
    assert loaded.cad_layout_readback.confirmed_by_role == Role.ENGINEER
    assert loaded.trough_section_layout == project.trough_section_layout
    assert loaded.parameters["trough_measured_section_count"].value == 4

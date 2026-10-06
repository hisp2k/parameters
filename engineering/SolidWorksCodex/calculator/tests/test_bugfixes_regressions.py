# -*- coding: utf-8 -*-
"""
Регрессионные тесты на конкретные ошибки, воспроизведённые в задании от
16.09.2026 ("ЗАДАНИЕ ДЛЯ CLAUDE: ПРОДОЛЖАЙ РАЗРАБОТКУ КАЛЬКУЛЯТОРА",
раздел 1). Каждый тест здесь называет ту же ошибку, что и в задании, и
проверяет, что она больше не воспроизводится — раздел 1 прямо требует:
"Добавь проверки, воспроизводящие эти ошибки. Успешные прежние 27 тестов
недостаточны."
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails, Abrasiveness,
    validate_questionnaire, unsupported_requirements,
)
from calculator.core.screw_engineering import (
    ScrewEngineeringInput, compute_engineering_core, EngineeringInputError,
)
from calculator.core.project import Project
from calculator.core.roles import Role, RoleContext, can
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.strength_coverage import VerificationMethod
from calculator.core.verification import VerificationRecord
from calculator.documents.agreement_sheet import build_agreement_sheet_data, render_html, build_pdf


def _valid_questionnaire(**overrides) -> QuestionnaireInput:
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


def _project_with_calc(q=None, forced_diameter_mm=None) -> Project:
    q = q or _valid_questionnaire(forced_diameter_mm=forced_diameter_mm)
    project = Project(project_name="Тест", customer="Заказчик", designation="test_regr")
    project.set_questionnaire(q)
    length, angle = q.geometry.resolved_length_angle()
    result = compute_engineering_core(ScrewEngineeringInput(
        productivity_value=q.productivity.value, productivity_unit=q.productivity.unit.value,
        bulk_density_kg_m3=q.material.bulk_density_kg_m3, max_lump_size_mm=q.material.max_lump_size_mm,
        is_sorted_material=q.material.is_sorted_material, abrasiveness=q.material.abrasiveness.value,
        working_length_mm=length, incline_deg=angle,
        forced_diameter_mm=q.forced_diameter_mm, forced_step_mm=q.forced_step_mm,
    ))
    project.record_engineering_result(result)
    return project


# --- 1.А: блокировка выпуска не снимается сменой булевых флагов -----------

def test_bug_a_setting_method_alone_does_not_close_strength_item():
    """Раньше `method = ANALYTICAL` без единого числа уже считалось 'закрыто'."""
    project = _project_with_calc()
    for item in project.strength_registry:
        item.method = VerificationMethod.ANALYTICAL  # объявили метод, но НЕ посчитали
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    assert any("BOM без подтверждённого" in r for r in reasons)


def test_bug_a_module_done_true_alone_does_not_pass_gate():
    """Раньше `ModuleStatus(done=True)` без исполнителя/доказательства уже считалось выполненным."""
    project = _project_with_calc()
    project.drive_selection.done = True  # прямая порча флага в обход mark_done()
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    assert any("Подбор привода" in r for r in reasons)


def test_bug_a_mark_done_requires_evidence():
    project = _project_with_calc()
    with pytest.raises(ValueError):
        project.drive_selection.mark_done(
            confirmed_by="", confirmed_by_role=Role.ENGINEER, evidence="",
            input_fingerprint="x", product_revision=project.revision,
        )


def test_bug_a_fully_verified_project_can_pass_gate():
    """Позитивный путь: если ВСЁ реально закрыто (не просто флагами), блокировок быть не должно."""
    project = _project_with_calc()
    fp = project.compute_input_fingerprint()

    from dataclasses import replace
    from calculator.core.strength_coverage import required_load_cases

    for index, item in enumerate(project.strength_registry, 1):
        # Synthetic BOM fixture: placeholders and one generic stress value do
        # not prove all checks. Classes without a catalog need explicit exclusion.
        item.bom_position = f"TEST-BOM-{index}"
        cases = required_load_cases(item.component_class)
        if not cases:
            item.method = VerificationMethod.NOT_APPLICABLE
            item.justification = "synthetic test assembly: this class is absent"
            item.justification_approved_by = "Инженер Петров"
            item.justification_approved_by_role = Role.ENGINEER
            continue
        item.method = VerificationMethod.ANALYTICAL
        item.verification = VerificationRecord(
            criterion_description=f"прочность: {item.component_class}",
            result_value=100.0, result_unit="МПа", criterion_limit=150.0,
            criterion_source="общеинженерная методика расчёта металлоконструкций",
            method="аналитический_расчёт", methodology_version="v1",
            input_fingerprint=fp, product_revision=project.revision,
            computed_by="Инженер Иванов", computed_by_role=Role.ENGINEER,
            reviewed_by="Инженер Петров", reviewed_by_role=Role.ENGINEER,
        )
        item.verifications = [replace(item.verification, criterion_description=case) for case in cases]
    project.engineer_confirmed_assumptions = True
    project.drive_selection.mark_done(
        confirmed_by="Инженер Иванов", confirmed_by_role=Role.ENGINEER,
        evidence="привод подобран по каталогу X", input_fingerprint=fp, product_revision=project.revision,
    )
    project.cad_sync.mark_done(
        confirmed_by="Инженер Иванов", confirmed_by_role=Role.ENGINEER,
        evidence="модель перестроена без ошибок", input_fingerprint=fp, product_revision=project.revision,
    )
    project.kd_bom.mark_done(
        confirmed_by="Инженер Иванов", confirmed_by_role=Role.ENGINEER,
        evidence="BOM выгружена", input_fingerprint=fp, product_revision=project.revision,
    )
    project.technology.mark_done(
        confirmed_by="Инженер Иванов", confirmed_by_role=Role.ENGINEER,
        evidence="техпроцессы разработаны", input_fingerprint=fp, product_revision=project.revision,
    )
    from calculator.core.project import TechnicalReview, ReleaseApproval
    project.technical_review = TechnicalReview(
        reviewer_name="Инженер Петров", reviewer_role=Role.ENGINEER,
        prepared_by_name="Инженер Иванов", input_fingerprint=fp, product_revision=project.revision,
    )
    project.release_approval = ReleaseApproval(approved_by_name="Руководитель Сидоров", product_revision=project.revision)

    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    assert reasons == [], f"Ожидали пустой список причин, получено: {reasons}"


# --- 1.Б: устаревшие результаты -------------------------------------------

def test_bug_b_changing_productivity_invalidates_calculation():
    """Изменение производительности с 5 до 100 т/ч должно аннулировать расчёт и поднять ревизию."""
    project = _project_with_calc()
    old_revision = project.revision
    assert project.engineering_result is not None

    new_q = _valid_questionnaire(productivity=ProductivityInput(value=100.0, unit=ProductivityUnit.T_H))
    invalidated = project.set_questionnaire(new_q, reason="изменение производительности 5->100 т/ч")

    assert invalidated is True
    assert project.engineering_result is None, "старый расчёт должен быть аннулирован, а не оставлен как актуальный"
    assert project.revision != old_revision, "ревизия должна подняться при аннулировании"
    assert project.drive_selection.done is False
    assert project.cad_sync.done is False


def test_bug_b_unchanged_questionnaire_does_not_bump_revision():
    """Пересохранение ТЕХ ЖЕ данных не должно аннулировать расчёт (иначе ревизия росла бы без причины)."""
    project = _project_with_calc()
    old_revision = project.revision
    same_q = _valid_questionnaire()  # те же значения, новый объект
    invalidated = project.set_questionnaire(same_q)
    assert invalidated is False
    assert project.revision == old_revision
    assert project.engineering_result is not None


def test_bug_b_stale_calc_detected_and_blocks_release():
    project = _project_with_calc()
    # Меняем анкету напрямую в обход set_questionnaire — имитирует прямую
    # порчу состояния (на случай, если где-то ещё в коде появится такой путь).
    project.questionnaire.productivity.value = 100.0
    assert project.is_calc_stale() is True
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    assert any("устарел" in r.lower() for r in reasons)


def test_bug_b_previously_issued_documents_marked_stale():
    project = _project_with_calc()
    project.issue_document("лист_согласования_pdf", "/tmp/old.pdf")
    new_q = _valid_questionnaire(productivity=ProductivityInput(value=100.0, unit=ProductivityUnit.T_H))
    project.set_questionnaire(new_q)
    stale = project.stale_issued_documents()
    assert len(stale) == 1
    assert stale[0].revision != project.revision


# --- 1.В: требуемая vs достижимая производительность -----------------------

def test_bug_c_forced_diameter_100mm_5th_shows_honest_achievable_value():
    """
    Из задания: "требование 5 т/ч и принудительном диаметре 100 мм ограничение
    оборотов даёт около 1,27 т/ч по собственной формуле программы, но в
    результате остаётся 5 т/ч." Проверяем, что теперь это НЕ так.
    """
    result = compute_engineering_core(ScrewEngineeringInput(
        productivity_value=5.0, productivity_unit="т/ч", bulk_density_kg_m3=700.0,
        max_lump_size_mm=15.0, is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM.value,
        working_length_mm=3000.0, incline_deg=0.0, forced_diameter_mm=100.0,
    ))
    assert result.productivity_required_t_per_h == 5.0
    assert result.productivity_achievable_t_per_h < 2.0, (
        f"достижимая производительность должна упасть примерно до 1.27 т/ч, "
        f"получено {result.productivity_achievable_t_per_h}"
    )
    assert math.isclose(result.productivity_achievable_t_per_h, 1.267, abs_tol=0.05)
    assert result.requirement_met is False
    assert result.rotation_speed_rpm == result.max_allowed_rotation_speed_rpm
    assert result.required_rotation_speed_rpm > result.max_allowed_rotation_speed_rpm
    assert any("НЕ выполняется" in w or "не будет достигнута" in w for w in result.warnings)


def test_bug_c_release_gate_blocks_when_requirement_not_met():
    project = _project_with_calc(forced_diameter_mm=100.0)
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    assert any("производительность не выполняется" in r.lower() for r in reasons)


# --- 1.Г: потеря входных данных (пуск под нагрузкой, реверс) ---------------

def test_bug_d_app_loader_preserves_optional_fields(tmp_path):
    """
    Раньше load_questionnaire_from_json() не читала секцию "optional" вообще —
    startup_under_load/reverse_required терялись молча.
    """
    import json
    import importlib
    app = importlib.import_module("calculator.app")

    payload = {
        "conveyor_kind": "валовый_желобчатый",
        "material": {
            "material_name": "тест", "bulk_density_kg_m3": 700.0, "max_lump_size_mm": 10.0,
            "is_sorted_material": False, "abrasiveness": "средняя",
        },
        "productivity": {"value": 5.0, "unit": "т/ч"},
        "geometry": {"mode": "длина_по_оси_и_угол", "working_length_mm": 3000.0, "incline_deg": 0.0},
        "profile": {"construction_material": "Ст3"},
        "optional": {"startup_under_load": True, "reverse_required": True},
    }
    p = tmp_path / "input.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    q = app.load_questionnaire_from_json(p)
    assert q.optional.startup_under_load is True, "пуск под нагрузкой не должен теряться при загрузке"
    assert q.optional.reverse_required is True, "реверс не должен теряться при загрузке"


def test_bug_d_unsupported_requirements_are_shown_not_ignored():
    q = _valid_questionnaire(optional=OptionalDetails(startup_under_load=True, reverse_required=True))
    warnings = unsupported_requirements(q)
    assert any("пуск под нагрузкой" in w.lower() for w in warnings)
    assert any("реверс" in w.lower() for w in warnings)


def test_bug_d_project_roundtrip_preserves_optional(tmp_path):
    q = _valid_questionnaire(optional=OptionalDetails(startup_under_load=True, reverse_required=True))
    project = Project(project_name="Т", customer="З", designation="opt_test")
    project.set_questionnaire(q)
    path = project.save(tmp_path / "opt_test.json")
    loaded = Project.load(path)
    assert loaded.questionnaire.optional.startup_under_load is True
    assert loaded.questionnaire.optional.reverse_required is True


# --- 1.Д: NaN/Infinity/типы -------------------------------------------------

def test_bug_e_nan_density_rejected_by_engineering_core():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(ScrewEngineeringInput(
            productivity_value=5.0, productivity_unit="т/ч", bulk_density_kg_m3=float("nan"),
            max_lump_size_mm=10.0, is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM.value,
            working_length_mm=3000.0, incline_deg=0.0,
        ))


def test_bug_e_infinity_productivity_rejected_by_engineering_core():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(ScrewEngineeringInput(
            productivity_value=float("inf"), productivity_unit="т/ч", bulk_density_kg_m3=700.0,
            max_lump_size_mm=10.0, is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM.value,
            working_length_mm=3000.0, incline_deg=0.0,
        ))


def test_bug_e_wrong_type_rejected_by_engineering_core():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(ScrewEngineeringInput(
            productivity_value="пять", productivity_unit="т/ч", bulk_density_kg_m3=700.0,
            max_lump_size_mm=10.0, is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM.value,
            working_length_mm=3000.0, incline_deg=0.0,
        ))


def test_bug_e_nan_density_rejected_by_questionnaire_validation():
    """
    `float('nan') <= 0` в Python — False, поэтому старая проверка "плотность
    больше нуля" молча пропускала NaN.
    """
    q = _valid_questionnaire()
    q.material.bulk_density_kg_m3 = float("nan")
    issues = validate_questionnaire(q)
    assert any("NaN" in i or "конечным числом" in i for i in issues)


def test_bug_e_infinite_working_length_rejected_by_questionnaire_validation():
    q = _valid_questionnaire()
    q.geometry.working_length_mm = float("inf")
    issues = validate_questionnaire(q)
    assert any("конечным числом" in i for i in issues)


# --- HTML/PDF: экранирование пользовательского текста -----------------------

def test_html_escapes_malicious_material_name(tmp_path):
    project = _project_with_calc(q=_valid_questionnaire(
        material=MaterialInput(
            material_name="<script>alert(1)</script>", bulk_density_kg_m3=700.0,
            max_lump_size_mm=15.0, is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM,
        ),
    ))
    data = build_agreement_sheet_data(project)
    html = render_html(data)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_pdf_builds_without_crashing_on_special_characters(tmp_path):
    project = _project_with_calc(q=_valid_questionnaire(customer="ООО \"Ромашка\" & <Ко>") if False else _valid_questionnaire())
    project.customer = "ООО \"Ромашка\" & <Ко> <b>bold-injection</b>"
    data = build_agreement_sheet_data(project)
    out = build_pdf(data, tmp_path / "test.pdf")
    assert out.exists()
    assert out.stat().st_size > 0


# --- кроссплатформенность PDF (шрифт из репозитория, не из ОС) -------------

def test_pdf_font_loaded_from_bundled_assets_not_system_path():
    from calculator.documents.agreement_sheet import ASSETS_FONT_DIR
    assert (ASSETS_FONT_DIR / "DejaVuSans.ttf").exists()
    assert (ASSETS_FONT_DIR / "DejaVuSans-Bold.ttf").exists()


# --- совмещение ролей должно быть явным ------------------------------------

def test_head_alone_does_not_get_engineer_permissions():
    """Раньше `can(Role.HEAD, "review_strength_and_drive")` было True автоматически."""
    assert can(Role.HEAD, "review_strength_and_drive") is False
    assert can(Role.HEAD, "rebuild_cad_project_copy") is False


def test_role_combination_must_be_explicit():
    ctx = RoleContext(person_name="Иванов И.И.", assigned_roles={Role.HEAD, Role.ENGINEER}, acting_as=Role.ENGINEER)
    assert ctx.can("review_strength_and_drive") is True
    ctx_head = RoleContext(person_name="Иванов И.И.", assigned_roles={Role.HEAD, Role.ENGINEER}, acting_as=Role.HEAD)
    assert ctx_head.can("review_strength_and_drive") is False


def test_role_combination_rejects_unassigned_role():
    with pytest.raises(PermissionError):
        RoleContext(person_name="Петров П.П.", assigned_roles={Role.MANAGER}, acting_as=Role.ENGINEER)

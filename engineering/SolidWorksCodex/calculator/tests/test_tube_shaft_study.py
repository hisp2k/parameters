# -*- coding: utf-8 -*-
"""
Проверка исследовательского расчёта вала TUBE-SAND-001
(core/tube_shaft_study.py) и его подключения к Project — раздел задания
"допустим исследовательский результат, но не закрытая позиция выпуска".

Ключевое требование, которое проверяет этот файл: прикрепление
TubeShaftInfluenceStudy к проекту НИКОГДА не меняет исход release_gate.py
или strength_coverage.py — это отдельное поле, не часть strength_registry.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.tube_shaft_study import (
    SUPPORT_SCHEME_ASSUMPTION, SPAN_SOURCE_NOTE, MISSING_FOR_REAL_SHAFT_RESULT,
    GravityDecomposition, TubeShaftInfluenceStudy, UnitLoadInfluenceCoefficients,
    build_tube_shaft_study, gravity_decomposition_for_scenarios, unit_load_influence_coefficients,
)
from calculator.core.shaft_beam_model import (
    PLANE_VERTICAL, BeamLoadCase, DistributedLoad, PointLoad, ShaftSupport,
    solve_reactions, solve_shear_moment,
)
from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, Abrasiveness,
)
from calculator.core.project import Project
from calculator.core.roles import Role
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.strength_coverage import uncovered as uncovered_strength_items
from calculator.core.tube_engineering import TubeEngineeringResult, TubeCalcStatus

# Подтверждённые сценарии эскиза (см. summary задания): L=2515 мм для обоих;
# A — угол эскиза 35°; B — угол, пересчитанный из заявленных высот пола
# (500 мм загрузка, 1500 мм выгрузка) при том же L=2515 мм.
_SPAN_MM = 2515.0
_ANGLE_A_DEG = 35.0
_RISE_B_MM = 1000.0
_ANGLE_B_DEG = math.degrees(math.asin(_RISE_B_MM / _SPAN_MM))


# --- геометрия/сценарии -----------------------------------------------------

def test_scenario_a_matches_sketch_angle_35_degrees():
    decompositions = gravity_decomposition_for_scenarios(_ANGLE_A_DEG, _ANGLE_B_DEG)
    scenario_a = next(g for g in decompositions if g.scenario_label == "сценарий_A_угол_эскиза")
    assert scenario_a.angle_deg == pytest.approx(35.0)


def test_scenario_b_matches_heights_derived_angle_about_23_43_degrees():
    decompositions = gravity_decomposition_for_scenarios(_ANGLE_A_DEG, _ANGLE_B_DEG)
    scenario_b = next(g for g in decompositions if g.scenario_label == "сценарий_B_угол_по_высотам")
    # asin(1000/2515) ≈ 23.4291° — тот же результат, что зафиксирован в
    # предыдущих этапах (geometry_conflict / GeometryConflictReport).
    assert scenario_b.angle_deg == pytest.approx(23.429122203943404, rel=1e-9)


def test_both_scenarios_are_kept_separate_neither_auto_selected():
    decompositions = gravity_decomposition_for_scenarios(_ANGLE_A_DEG, _ANGLE_B_DEG)
    assert len(decompositions) == 2
    labels = {g.scenario_label for g in decompositions}
    assert labels == {"сценарий_A_угол_эскиза", "сценарий_B_угол_по_высотам"}


def test_gravity_decomposition_uses_cos_sin_of_angle():
    decompositions = gravity_decomposition_for_scenarios(_ANGLE_A_DEG, _ANGLE_B_DEG)
    for g in decompositions:
        rad = math.radians(g.angle_deg)
        assert g.transverse_component_factor == pytest.approx(math.cos(rad))
        assert g.axial_component_factor == pytest.approx(math.sin(rad))
        # cos²+sin²=1 — sanity, не выдуманная формула разложения.
        assert g.transverse_component_factor ** 2 + g.axial_component_factor ** 2 == pytest.approx(1.0)


# --- коэффициенты влияния: согласованность с shaft_beam_model напрямую -----

def _direct_unit_udl_reaction_and_moment(span_mm: float):
    supports = [ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span_mm, axially_fixed=False)]
    case = BeamLoadCase(
        total_length_mm=span_mm, supports=supports,
        distributed_loads=[DistributedLoad(0.0, span_mm, 1.0, PLANE_VERTICAL)],
    )
    reactions = solve_reactions(case, PLANE_VERTICAL)
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    return reactions.support_a_n, solution.moment(span_mm / 2.0)


def _direct_unit_point_reaction_and_moment(span_mm: float):
    supports = [ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span_mm, axially_fixed=False)]
    case = BeamLoadCase(
        total_length_mm=span_mm, supports=supports,
        point_loads=[PointLoad(span_mm / 2.0, 1.0, PLANE_VERTICAL)],
    )
    reactions = solve_reactions(case, PLANE_VERTICAL)
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    return reactions.support_a_n, solution.moment(span_mm / 2.0)


def test_unit_load_coefficients_match_direct_shaft_beam_model_calls():
    """
    Коэффициенты влияния — НЕ отдельная (потенциально расходящаяся с
    решателем) арифметика, а прямой вызов той же схемы core/shaft_beam_model.py.
    """
    coeffs = unit_load_influence_coefficients(_SPAN_MM)
    ref_udl_reaction, ref_udl_moment = _direct_unit_udl_reaction_and_moment(_SPAN_MM)
    ref_point_reaction, ref_point_moment = _direct_unit_point_reaction_and_moment(_SPAN_MM)

    assert coeffs.reaction_per_unit_udl_n == pytest.approx(ref_udl_reaction)
    assert coeffs.moment_max_per_unit_udl_nmm == pytest.approx(ref_udl_moment)
    assert coeffs.reaction_per_unit_point_n == pytest.approx(ref_point_reaction)
    assert coeffs.moment_max_per_unit_point_nmm == pytest.approx(ref_point_moment)


def test_unit_load_coefficients_match_textbook_closed_form_for_this_span():
    """Дополнительная сверка с закрытой формой (wL/2 и wL²/8, P/2 и PL/4) на конкретном пролёте 2515 мм."""
    coeffs = unit_load_influence_coefficients(_SPAN_MM)
    w = 1.0  # Н/мм, единичная УДН
    p = 1.0  # Н, единичная точечная сила
    assert coeffs.reaction_per_unit_udl_n == pytest.approx(w * _SPAN_MM / 2.0)
    assert coeffs.moment_max_per_unit_udl_nmm == pytest.approx(w * _SPAN_MM ** 2 / 8.0)
    assert coeffs.reaction_per_unit_point_n == pytest.approx(p / 2.0)
    assert coeffs.moment_max_per_unit_point_nmm == pytest.approx(p * _SPAN_MM / 4.0)


# --- полный отчёт ------------------------------------------------------------

def test_build_tube_shaft_study_uses_confirmed_span_2515mm():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    assert study.span_mm == pytest.approx(2515.0)
    assert study.influence_coefficients.span_mm == pytest.approx(2515.0)


def test_build_tube_shaft_study_is_flagged_exploratory_and_non_closing():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    assert study.is_exploratory is True
    assert study.closes_release_gate_item is False


def test_build_tube_shaft_study_lists_missing_inputs_for_real_result():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    assert study.missing_for_real_result == MISSING_FOR_REAL_SHAFT_RESULT
    assert len(study.missing_for_real_result) == 7
    joined = " ".join(study.missing_for_real_result)
    # Каждый пункт из summary задания должен быть покрыт (диаметр, материал,
    # погонная масса, опоры, крутящий момент/привод, осевое усилие, продукт).
    for keyword in ("сечение", "материал", "погонная масса", "опор", "крутящий момент", "осевое усилие"):
        assert keyword in joined


def test_build_tube_shaft_study_declines_numeric_torque_path_due_to_drive_conflict():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    assert study.drive_torque_path_note
    assert "конфликт" in study.drive_torque_path_note.lower() or "не рассчита" in study.drive_torque_path_note.lower()


def test_build_tube_shaft_study_carries_support_scheme_and_span_source_disclaimers():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    assert study.support_scheme_assumption == SUPPORT_SCHEME_ASSUMPTION
    assert study.span_source_note == SPAN_SOURCE_NOTE
    assert "допущен" in study.support_scheme_assumption.lower()
    assert "2515" in study.span_source_note


def test_tube_shaft_study_roundtrip_to_dict_from_dict():
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    restored = TubeShaftInfluenceStudy.from_dict(study.to_dict())
    assert restored == study


# --- подключение к Project: НЕ влияет на release_gate/strength_coverage ----

def _sample_tube_project() -> Project:
    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(
            material_name="вода с песком", bulk_density_kg_m3=1500.0, max_lump_size_mm=2.0,
            is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=10.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=_SPAN_MM, incline_deg=_ANGLE_A_DEG),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    return Project(project_name="TUBE-SAND-001 (тест)", customer="Тех-Аэро", designation="TUBE-SAND-001-test", questionnaire=q)


def test_record_tube_shaft_study_attaches_and_touches_project():
    project = _sample_tube_project()
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    before_updated_at = project.updated_at
    project.record_tube_shaft_study(study)
    assert project.tube_shaft_study is study
    assert project.updated_at >= before_updated_at


def test_record_tube_shaft_study_rejects_a_non_exploratory_or_closing_study():
    project = _sample_tube_project()
    closing_variant = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    closing_variant.closes_release_gate_item = True
    with pytest.raises(ValueError):
        project.record_tube_shaft_study(closing_variant)

    non_exploratory_variant = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    non_exploratory_variant.is_exploratory = False
    with pytest.raises(ValueError):
        project.record_tube_shaft_study(non_exploratory_variant)


def test_shaft_study_never_affects_release_gate():
    """
    Прикрепление исследовательского расчёта вала не должно менять НИ ОДНУ
    причину блокировки release_gate.evaluate() — она обязана остаться
    буквально тем же списком (не просто "той же длины").
    """
    project_without = _sample_tube_project()
    reasons_without = evaluate_release_gate(project_without, requesting_role=Role.HEAD)

    project_with = _sample_tube_project()
    project_with.record_tube_shaft_study(build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG))
    reasons_with = evaluate_release_gate(project_with, requesting_role=Role.HEAD)

    assert reasons_with == reasons_without
    assert len(reasons_with) > 0  # проект без расчёта/подтверждений и так заблокирован — сравниваем неизменность


def test_shaft_study_never_affects_strength_coverage():
    project_without = _sample_tube_project()
    input_fp = project_without.compute_input_fingerprint()
    uncovered_without = uncovered_strength_items(project_without.strength_registry, project_without.revision, input_fp)

    project_with = _sample_tube_project()
    project_with.record_tube_shaft_study(build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG))
    uncovered_with = uncovered_strength_items(project_with.strength_registry, project_with.revision, input_fp)

    assert [item.component_class for item in uncovered_with] == [item.component_class for item in uncovered_without]
    # Само поле study никогда не является частью strength_registry.
    assert all(not hasattr(item, "tube_shaft_study") for item in project_with.strength_registry)


def test_project_roundtrip_save_load_persists_tube_shaft_study(tmp_path):
    project = _sample_tube_project()
    project.record_tube_shaft_study(build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG))
    path = project.save(tmp_path / "tube_sand_001_test.json")
    loaded = Project.load(path)

    assert loaded.tube_shaft_study is not None
    assert loaded.tube_shaft_study == project.tube_shaft_study


def test_project_roundtrip_without_study_leaves_field_none(tmp_path):
    project = _sample_tube_project()
    path = project.save(tmp_path / "tube_sand_001_no_study.json")
    loaded = Project.load(path)
    assert loaded.tube_shaft_study is None


def test_questionnaire_change_invalidates_tube_shaft_study():
    """
    Раздел 1.Б задания: смена анкеты аннулирует зависимые результаты — вал
    посчитан по ПРИНЯТОМУ (не подтверждённому) пролёту/сценариям, поэтому
    смена геометрии должна очистить study вместе с остальными расчётами,
    а не оставить устаревший результат как будто он всё ещё актуален.
    """
    project = _sample_tube_project()
    # set_questionnaire() аннулирует только когда уже есть "подтверждённый"
    # расчёт (engineering_result ИЛИ tube_engineering_result, см. project.py) —
    # честный BLOCKED-результат тоже считается таким расчётом.
    project.record_tube_engineering_result(TubeEngineeringResult(
        status=TubeCalcStatus.BLOCKED, blockers=["методика для трубы на 35° не подтверждена"],
    ))
    study = build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG)
    project.record_tube_shaft_study(study)
    assert project.tube_shaft_study is not None

    new_q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(
            material_name="вода с песком", bulk_density_kg_m3=1500.0, max_lump_size_mm=2.0,
            is_sorted_material=False, abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=20.0, unit=ProductivityUnit.T_H),  # изменено
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=_SPAN_MM, incline_deg=_ANGLE_A_DEG),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    invalidated = project.set_questionnaire(new_q, reason="тест: изменена производительность")
    assert invalidated is True
    assert project.tube_shaft_study is None


def test_invalidate_downstream_directly_clears_tube_shaft_study():
    project = _sample_tube_project()
    project.record_tube_shaft_study(build_tube_shaft_study(_SPAN_MM, _ANGLE_A_DEG, _ANGLE_B_DEG))
    project._invalidate_downstream("тест: прямой вызов аннулирования")
    assert project.tube_shaft_study is None

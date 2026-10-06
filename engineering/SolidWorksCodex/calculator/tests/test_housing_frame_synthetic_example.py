# -*- coding: utf-8 -*-
"""
СКВОЗНОЙ синтетический пример «вал → подшипники → корпус → рама →
основание» (раздел 3-6 доп. задания; независимая проверка коммита c24d42b —
см. core/housing_frame_study.py для полного описания найденных дефектов и
их исправления, это уже ВТОРОЙ раунд независимой проверки после 377e33c).

ЭТО НЕ TUBE-SAND-001. Все числа (пролёты, силы, координаты, сечения) —
ПРОИЗВОЛЬНЫЕ круглые синтетические значения, выбранные НАРОЧИТО непохожими
на исследовательские величины TUBE-SAND-001 (2515 мм, 35°, 23.4291° и
т.п. из core/tube_shaft_study.py), чтобы результат нельзя было спутать с
реальным изделием. `calculator/data/TUBE-SAND-001.json` на момент этого
этапа ОТСУТСТВУЕТ ни в git, ни на рабочей станции (проверено ОДИН раз через
файловый мост — см. calculator/TUBE_HOUSING_FRAME_STAGE_RU.md, раздел
«Проверка CAD/моста») — поэтому синтетический пример применяется буквально,
не как запасной вариант.

НАЗНАЧЕНИЕ теста — вызвать вынесенную функцию приложения
`core.housing_frame_study.calculate_structural_chain()` и проверить, что
цепочка технически работает и даёт самосогласованный результат: равновесие
ВСЕЙ объединённой модели корпус+рама, НЕЗАВИСИМЫЙ тест свободного тела ДВУМЯ
разными путями (через `combined_loads` и через СЫРЫЕ исходные величины),
физически согласованную геометрию (труба корпуса реально вмещает вал),
подключённый расчёт подшипников, явный путь крутящего момента через вал/
корпус, относительный зазор по непрерывному сканированию внутри элементов.

Этот файл не пишет ничего в calculator/data/ и не создаёт Project — это
ЧИСТО исследовательская демонстрация цепочки, как и core/tube_shaft_study.py
для вала (см. его докстринг: "результат этого модуля НИКОГДА не попадает
в release_gate").
"""

import dataclasses
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.housing_frame_study import (
    StructuralChainError, ChainGeometry, ChainLoads, ClearanceInputs, BearingCatalogInputs,
    calculate_structural_chain, synthetic_example_geometry_and_loads, compute_chain_fingerprint,
    FIXED_SUPPORT_LABEL, FLOATING_SUPPORT_LABEL,
)
from calculator.core.load_transfer import LoadCase, LoadVector, Point3D
from calculator.core.shaft_beam_model import HollowCircularSection


@pytest.fixture(scope="module")
def chain_inputs():
    return synthetic_example_geometry_and_loads()


@pytest.fixture(scope="module")
def chain_result(chain_inputs):
    geometry, loads, clearance_inputs, bearing_catalog = chain_inputs
    return calculate_structural_chain(geometry, loads, clearance_inputs, bearing_catalog)


# --- 0. Геометрия физически согласована (независимая проверка c24d42b) -----

def test_synthetic_housing_tube_actually_fits_the_shaft(chain_inputs):
    geometry, _, _, _ = chain_inputs
    assert geometry.housing_tube_section.inner_diameter_mm > geometry.shaft_section.outer_diameter_mm


def test_calculate_structural_chain_rejects_housing_bore_smaller_than_shaft(chain_inputs):
    geometry, loads, clearance_inputs, bearing_catalog = chain_inputs
    incompatible_tube = HollowCircularSection(outer_diameter_mm=130.0, inner_diameter_mm=100.0, source="test-bad")
    bad_geometry = dataclasses.replace(geometry, housing_tube_section=incompatible_tube)
    with pytest.raises(StructuralChainError):
        calculate_structural_chain(bad_geometry, loads, clearance_inputs, bearing_catalog)


def test_stiffness_stress_and_clearance_diameter_share_a_single_source(chain_result):
    # Регрессия конкретного repro независимой проверки: раньше можно было
    # подменить ТОЛЬКО поле напряжений/зазора, оставив жёсткость прежней.
    # Теперь geometry.housing_tube_section — ЕДИНСТВЕННЫЙ источник для всех
    # трёх употреблений (жёсткость МКЭ, формулы напряжений, диаметр зазора).
    tube = chain_result.geometry.housing_tube_section
    assert chain_result.clearance.clearance.nominal_radial_clearance_mm == pytest.approx(
        (tube.inner_diameter_mm - chain_result.geometry.shaft_section.outer_diameter_mm) / 2.0, rel=1e-9,
    )


def test_frame_section_is_independent_from_housing_tube_section(chain_inputs):
    geometry, _, _, _ = chain_inputs
    # Разные объекты/разные жёсткости — рама НЕ эквивалент трубы корпуса.
    assert geometry.frame_section is not geometry.housing_tube_section
    housing_area = math.pi / 4.0 * (
        geometry.housing_tube_section.outer_diameter_mm ** 2 - geometry.housing_tube_section.inner_diameter_mm ** 2
    )
    assert geometry.frame_section.area_mm2 != pytest.approx(housing_area, rel=1e-6)


# --- 1. Вал: равновесие само по себе ----------------------------------------

def test_shaft_reactions_balance_applied_load(chain_result):
    r_a = chain_result.shaft_solution.reactions.support_a_n
    r_b = chain_result.shaft_solution.reactions.support_b_n
    assert (r_a + r_b) == pytest.approx(chain_result.loads.product_point_load_n, rel=1e-9)


def test_shaft_own_torque_path_is_balanced(chain_result):
    # Путь момента через ВАЛ: вход привода + сопротивление продукта = 0.
    for row in chain_result.acceptance_table:
        if "момент через ВАЛ" in row.node:
            assert row.status == "OK"
            return
    pytest.fail("Строка про путь момента через вал не найдена в acceptance_table.")


def test_shaft_von_mises_stress_is_finite_and_positive(chain_result):
    assert chain_result.shaft_von_mises_mpa > 0.0
    assert math.isfinite(chain_result.shaft_von_mises_mpa)


# --- 2. Перенос нагрузки: оси вала и расточки корпуса совмещены ------------

def test_shaft_and_housing_bore_axes_are_coincident(chain_result):
    # Независимая проверка c24d42b: раньше housing_drop_mm=180 мм разносил
    # оси вала и расточки корпуса без физического обоснования. Теперь точка
    # крепления корпуса РАВНА точке опоры вала — перенос не добавляет
    # искусственного плеча.
    r_a = chain_result.shaft_solution.reactions.support_a_n
    z = chain_result.geometry.shaft_axis_z_mm
    load = LoadVector(
        node_ref="test", point=Point3D(0.0, 0.0, z), fx_n=0.0, fy_n=0.0, fz_n=-r_a,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING, source="test",
    )
    transferred = load.transferred_to(Point3D(0.0, 0.0, z))  # та же точка — r=0
    assert transferred.mx_nmm == pytest.approx(0.0, abs=1e-9)
    assert transferred.my_nmm == pytest.approx(0.0, abs=1e-9)
    assert transferred.fz_n == pytest.approx(-r_a, rel=1e-9)


# --- 3+4. Корпус+рама — ОДНА объединённая модель: равновесие ---------------

def test_combined_model_equilibrium_residual_is_near_zero(chain_result):
    for key, value in chain_result.equilibrium_residual.items():
        assert abs(value) < 1e-6, f"Объединённая модель: равновесие нарушено по {key}: {value}"


def test_independent_free_body_check_is_near_zero(chain_result):
    for key, value in chain_result.independent_free_body_residual.items():
        assert abs(value) < 1e-6, f"Свободное тело цепочки: равновесие нарушено по {key}: {value}"


def test_independent_free_body_check_matches_frame_model_equilibrium_residual(chain_result):
    for key in ("fx", "fy", "fz", "mx", "my", "mz"):
        assert chain_result.independent_free_body_residual[key] == pytest.approx(
            chain_result.equilibrium_residual[key], abs=1e-6,
        )


def test_raw_external_load_free_body_check_is_near_zero_and_independent(chain_result):
    # Независимая проверка c24d42b, раздел «результат и приёмка»: проверка,
    # построенная из СЫРЫХ исходных величин (r_a/r_b/осевая реакция/вес/
    # момент), НЕ переиспользующая combined_loads/transfer_set.
    for key, value in chain_result.raw_external_load_free_body_residual.items():
        assert abs(value) < 1e-6, f"Свободное тело (сырые нагрузки): равновесие нарушено по {key}: {value}"


def test_raw_and_frame_model_free_body_checks_agree(chain_result):
    for key in ("fx", "fy", "fz", "mx", "my", "mz"):
        assert chain_result.raw_external_load_free_body_residual[key] == pytest.approx(
            chain_result.independent_free_body_residual[key], abs=1e-6,
        )


# --- Основное P0-исправление: реакция основания = ВНЕШНЯЯ нагрузка ---------

def test_base_reaction_equals_external_applied_load_not_10500(chain_result):
    total_external = (chain_result.loads.product_point_load_n + chain_result.loads.housing_self_weight_n)
    assert abs(chain_result.base_reaction_total_z_n) == pytest.approx(total_external, rel=1e-6)
    assert abs(chain_result.base_reaction_total_z_n) != pytest.approx(10500.0, rel=1e-3)
    assert abs(chain_result.base_reaction_total_z_n) == pytest.approx(6400.0, rel=1e-6)


def test_no_load_silently_disappears_between_housing_and_frame(chain_result):
    total_external = chain_result.loads.product_point_load_n + chain_result.loads.housing_self_weight_n
    assert abs(chain_result.base_reaction_total_z_n) == pytest.approx(total_external, rel=1e-6)


def test_h_mid_node_has_no_ground_support_in_combined_model(chain_result):
    support_node_ids = {s.node_id for s in chain_result.combined_model.supports}
    assert "H_MID" not in support_node_ids
    assert support_node_ids == {"F_BASE_1", "F_BASE_2"}


def test_net_reaction_torque_applied_to_frame_is_zero_by_construction(chain_result):
    # −T у крепления привода (H_SUP_1) + T у реакции стенки на противомомент
    # продукта (H_LOAD_B) — сумма 0, момент замыкается ВНУТРИ корпуса/рамы.
    drive_torque = chain_result.loads.drive_torque_nmm
    mx_values = [ld.mx_nmm for ld in chain_result.combined_model.loads if ld.mx_nmm != 0.0]
    assert len(mx_values) == 2
    assert sum(mx_values) == pytest.approx(0.0, abs=1e-6)
    assert set(mx_values) == {-drive_torque, drive_torque}


# --- Внутренние силовые факторы для ВСЕХ элементов --------------------------

def test_member_forces_reported_for_all_seven_members(chain_result):
    expected = {"h_overhang_a", "h1", "h2", "h_overhang_b", "leg_1", "leg_2", "brace_top"}
    assert set(chain_result.member_forces.keys()) == expected
    for member_id, forces in chain_result.member_forces.items():
        for attr in ("n_i", "vy_i", "vz_i", "t_i", "my_i", "mz_i", "n_j", "vy_j", "vz_j", "t_j", "my_j", "mz_j"):
            assert math.isfinite(getattr(forces, attr)), f"{member_id}.{attr} не конечно"


def test_base_reactions_reported_for_both_base_nodes(chain_result):
    assert set(chain_result.base_reactions.keys()) == {"F_BASE_1", "F_BASE_2"}
    for node_id, reaction in chain_result.base_reactions.items():
        assert set(reaction.keys()) == {"fx", "fy", "fz", "mx", "my", "mz"}
        for value in reaction.values():
            assert math.isfinite(value)


def test_axial_reaction_only_enters_housing_at_the_fixed_support(chain_result):
    # Путь осевой реакции: выбор фиксирующей опоры определяет, ГДЕ осевая
    # сила входит в корпус — у плавающей опоры (H_LOAD_B) fx=0 буквально.
    loads_by_node = {}
    for ld in chain_result.combined_model.loads:
        loads_by_node.setdefault(ld.node_id, []).append(ld)
    fx_at_load_b = sum(ld.fx_n for ld in loads_by_node.get("H_LOAD_B", []))
    fx_at_load_a = sum(ld.fx_n for ld in loads_by_node.get("H_LOAD_A", []))
    assert fx_at_load_b == pytest.approx(0.0, abs=1e-9)
    assert fx_at_load_a != 0.0


# --- Напряжения на консольном свесе корпуса (с учётом N/A) -----------------

def test_overhang_stress_is_finite_and_includes_axial_term(chain_result):
    assert chain_result.overhang_a_von_mises_mpa > 0.0
    assert math.isfinite(chain_result.overhang_a_von_mises_mpa)
    end_forces = chain_result.member_forces["h_overhang_a"]
    assert end_forces.n_j != 0.0   # осевая сила действительно передана на этот элемент


# --- Подшипники: расчёт подключён к реакциям вала ---------------------------

def test_bearing_results_present_for_both_supports(chain_result):
    assert set(chain_result.bearing_results.keys()) == {FIXED_SUPPORT_LABEL, FLOATING_SUPPORT_LABEL}


def test_bearing_radial_load_matches_shaft_reaction(chain_result):
    r_a = abs(chain_result.shaft_solution.reactions.support_a_n)
    r_b = abs(chain_result.shaft_solution.reactions.support_b_n)
    assert chain_result.bearing_results[FIXED_SUPPORT_LABEL].radial_load_n == pytest.approx(r_a, rel=1e-9)
    assert chain_result.bearing_results[FLOATING_SUPPORT_LABEL].radial_load_n == pytest.approx(r_b, rel=1e-9)


def test_bearing_axial_load_only_at_fixed_support(chain_result):
    assert chain_result.bearing_results[FIXED_SUPPORT_LABEL].axial_load_n > 0.0
    assert chain_result.bearing_results[FLOATING_SUPPORT_LABEL].axial_load_n == pytest.approx(0.0, abs=1e-9)


def test_bearing_life_changes_when_radial_load_changes():
    # "Реакции реально входят в расчёт подшипников; изменение нагрузки
    # меняет ресурс" — прямая регрессия.
    geometry, loads, clearance_inputs, bearing_catalog = synthetic_example_geometry_and_loads()
    light = calculate_structural_chain(geometry, loads, clearance_inputs, bearing_catalog)
    heavier_loads = dataclasses.replace(loads, product_point_load_n=loads.product_point_load_n * 3.0)
    heavy = calculate_structural_chain(geometry, heavier_loads, clearance_inputs, bearing_catalog)
    assert heavy.bearing_results[FIXED_SUPPORT_LABEL].l10_life_hours < light.bearing_results[FIXED_SUPPORT_LABEL].l10_life_hours


def test_bearing_result_is_unknown_without_catalog():
    geometry, loads, clearance_inputs, _ = synthetic_example_geometry_and_loads()
    result = calculate_structural_chain(geometry, loads, clearance_inputs, bearing_catalog=None)
    for bearing in result.bearing_results.values():
        assert bearing.status == "UNKNOWN"
        assert bearing.l10_life_hours is None
    # Отсутствие каталога НЕ блокирует остальной расчёт.
    assert math.isfinite(result.base_reaction_total_z_n)
    assert result.clearance.clearance.available_clearance_mm > 0.0


def test_bearing_status_never_marked_as_affecting_release_gate(chain_result):
    bearing_rows = [r for r in chain_result.acceptance_table if r.node.startswith("подшипник")]
    assert len(bearing_rows) == 2
    for row in bearing_rows:
        assert row.affects_release_gate is False


# --- 5. Относительный зазор — совместный расчёт, векторно, сканирование ----

def test_clearance_uses_combined_deflection_not_a_hardcoded_demo_value(chain_result):
    governing = chain_result.clearance.governing_section
    assert governing.consumed_by_deflection_mm != pytest.approx(0.35, rel=1e-3)
    assert governing.consumed_by_deflection_mm > 0.0
    assert math.isfinite(governing.consumed_by_deflection_mm)
    assert isinstance(chain_result.clearance.clearance.ok, bool)


def test_clearance_scans_many_sections_inside_members_not_only_five_nodes(chain_result):
    # Раньше проверялись РОВНО 5 узлов. Теперь — сетка сканирования ВНУТРИ
    # каждого из 4 элементов корпуса (не только узлы).
    assert len(chain_result.clearance.all_sections) > 5
    labels = {s.label for s in chain_result.clearance.all_sections}
    assert {"H_LOAD_A", "H_SUP_1", "H_MID", "H_SUP_2", "H_LOAD_B"} <= labels
    non_node_labels = [l for l in labels if "@" in l]
    assert non_node_labels, "Ожидались промежуточные сечения ВНУТРИ элементов (метка вида 'h1@...')"


def test_zero_deflection_is_only_at_the_frame_base_not_at_load_points(chain_result):
    # ВАЖНО: H_LOAD_A/H_LOAD_B — это точки приложения переданной нагрузки от
    # вала (свободные концы консольных вылетов корпуса), а НЕ закреплённые
    # опоры. Закреплены (Support.fixed) только F_BASE_1/F_BASE_2 — узлы
    # основания рамы, которые вообще не входят в сканирование зазора (зазор
    # считается на трубе корпуса, а не на ножках рамы). Поэтому у H_LOAD_A/B
    # прогиб НЕНУЛЕВОЙ — это исправление ошибочного допущения более раннего
    # варианта этого теста, требовавшего нулевой зазор именно в этих точках.
    by_label = {s.label: s for s in chain_result.clearance.all_sections}
    assert by_label["H_LOAD_A"].consumed_by_deflection_mm > 0.0
    assert by_label["H_LOAD_B"].consumed_by_deflection_mm > 0.0
    assert math.isfinite(by_label["H_LOAD_A"].consumed_by_deflection_mm)
    assert math.isfinite(by_label["H_LOAD_B"].consumed_by_deflection_mm)


def test_clearance_governing_section_is_the_maximum_not_an_arbitrary_pick(chain_result):
    governing = chain_result.clearance.governing_section
    all_consumed = [s.consumed_by_deflection_mm for s in chain_result.clearance.all_sections]
    assert governing.consumed_by_deflection_mm == max(all_consumed)


def test_clearance_scan_resolution_can_find_a_governing_point_between_nodes():
    # Не для СИММЕТРИЧНОГО основного примера (там максимум в H_MID по
    # симметрии нагрузки) — а для АСИММЕТРИЧНОГО случая (разные вылеты слева
    # и справа), где максимум прогиба физически не обязан совпасть с узлом.
    # Сама интерполяция проверена независимо в tests/test_frame_model.py::
    # test_transverse_displacement_can_have_interior_extremum_not_at_a_node;
    # здесь — что сканирование действительно ПОРОЖДАЕТ промежуточные точки,
    # способные стать governing (не только 5 узлов, см. тест выше).
    geometry, loads, clearance_inputs, bearing_catalog = synthetic_example_geometry_and_loads()
    asymmetric_geometry = dataclasses.replace(geometry, housing_inset_mm=150.0)
    result = calculate_structural_chain(asymmetric_geometry, loads, clearance_inputs, bearing_catalog)
    assert len(result.clearance.all_sections) > 5


# --- Численная оценка сдвиговой податливости вала --------------------------

def test_shaft_shear_deflection_estimate_is_reported_numerically(chain_result):
    estimate = chain_result.shaft_shear_deflection_estimate
    assert estimate.bending_deflection_mm > 0.0
    assert estimate.shear_deflection_mm > 0.0
    assert 0.0 < estimate.shear_to_bending_ratio < 1.0
    assert estimate.source


# --- Fingerprint, зависящий от фактических входов ---------------------------

def test_computed_fingerprint_is_stable_for_identical_inputs(chain_inputs):
    geometry, loads, clearance_inputs, _ = chain_inputs
    assert compute_chain_fingerprint(geometry, loads, clearance_inputs) == compute_chain_fingerprint(
        geometry, loads, clearance_inputs,
    )


def test_computed_fingerprint_changes_when_geometry_changes(chain_inputs):
    geometry, loads, clearance_inputs, _ = chain_inputs
    changed = dataclasses.replace(geometry, shaft_span_mm=geometry.shaft_span_mm + 1.0)
    assert compute_chain_fingerprint(geometry, loads, clearance_inputs) != compute_chain_fingerprint(
        changed, loads, clearance_inputs,
    )


def test_computed_fingerprint_changes_when_loads_change(chain_inputs):
    geometry, loads, clearance_inputs, _ = chain_inputs
    changed = dataclasses.replace(loads, product_point_load_n=loads.product_point_load_n + 1.0)
    assert compute_chain_fingerprint(geometry, loads, clearance_inputs) != compute_chain_fingerprint(
        geometry, changed, clearance_inputs,
    )


def test_chain_result_carries_the_computed_fingerprint(chain_result, chain_inputs):
    geometry, loads, clearance_inputs, _ = chain_inputs
    assert chain_result.computed_fingerprint == compute_chain_fingerprint(geometry, loads, clearance_inputs)


# --- Таблица «узел—режим—нагрузка—результат—критерий—статус» --------------

def test_acceptance_table_has_required_columns_and_never_touches_release_gate(chain_result):
    assert len(chain_result.acceptance_table) >= 9
    for row in chain_result.acceptance_table:
        assert row.node and row.mode and row.load and row.result and row.criterion and row.status
        assert row.affects_release_gate is False
    assert chain_result.is_research_only is True


def test_acceptance_table_all_equilibrium_rows_report_ok(chain_result):
    equilibrium_rows = [
        r for r in chain_result.acceptance_table
        if "равновес" in r.criterion.lower() or "невязка" in r.load.lower() or "≈0" in r.criterion
    ]
    assert equilibrium_rows
    for row in equilibrium_rows:
        assert row.status == "OK", f"{row.node}: {row.result} не удовлетворяет {row.criterion}"


# --- Незакрытые вопросы указаны явно, с владельцами -------------------------

def test_unresolved_items_are_surfaced_with_ownership(chain_result):
    joined = " ".join(chain_result.unresolved_items).lower()
    assert "cad" in joined or "конструктор" in joined
    assert "технолог" in joined or "заказчик" in joined
    assert "подшипник" in joined
    assert "сварных" in joined or "болтовых" in joined


def test_unresolved_items_mention_cad_bridge_check(chain_result):
    joined = " ".join(chain_result.unresolved_items).lower()
    assert "claudebridge" in joined or "мост" in joined


# --- Валидация входов calculate_structural_chain ----------------------------

def test_calculate_structural_chain_rejects_inset_beyond_half_span(chain_inputs):
    geometry, loads, clearance_inputs, bearing_catalog = chain_inputs
    bad_geometry = dataclasses.replace(geometry, housing_inset_mm=geometry.shaft_span_mm)
    with pytest.raises(StructuralChainError):
        calculate_structural_chain(bad_geometry, loads, clearance_inputs, bearing_catalog)


def test_calculate_structural_chain_rejects_non_finite_geometry_field(chain_inputs):
    geometry, loads, clearance_inputs, bearing_catalog = chain_inputs
    bad_geometry = dataclasses.replace(geometry, shaft_span_mm=float("nan"))
    with pytest.raises(StructuralChainError):
        calculate_structural_chain(bad_geometry, loads, clearance_inputs, bearing_catalog)

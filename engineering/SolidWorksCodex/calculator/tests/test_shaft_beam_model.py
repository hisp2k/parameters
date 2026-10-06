# -*- coding: utf-8 -*-
"""
Проверка решателя балочной модели (core/shaft_beam_model.py) на ЗАКРЫТЫХ
ФОРМУЛАХ сопромата — полностью синтетические данные, НЕ TUBE-SAND-001.
Раздел задания: "Добавь проверку решателя на известной балочной задаче,
равновесие сил/моментов, полое сечение, единицы и направление критериев".
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.shaft_beam_model import (
    HollowCircularSection, ShaftSupport, PointLoad, DistributedLoad, AxialLoad,
    AppliedTorque, BeamLoadCase, ShaftBeamModelError,
    SectionSegment, SteppedShaftProfile,
    solve_reactions, solve_shear_moment, solve_deflection, solve_twist_angle,
    bending_stress_mpa, torsional_shear_stress_mpa, combined_von_mises_stress_mpa,
    torque_diagram, torque_equilibrium_residual,
    critical_speed_rpm, buckling_applicability, clearance_check,
    central_point_load_shear_deflection_estimate,
    PLANE_VERTICAL, PLANE_HORIZONTAL,
)


# --- геометрия сечения ------------------------------------------------------

def test_hollow_section_matches_closed_form_solid_and_annulus():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    expected_area = math.pi / 4.0 * (100.0 ** 2 - 80.0 ** 2)
    expected_i = math.pi / 64.0 * (100.0 ** 4 - 80.0 ** 4)
    assert section.area_mm2 == pytest.approx(expected_area, rel=1e-9)
    assert section.moment_of_inertia_mm4 == pytest.approx(expected_i, rel=1e-9)
    # Полярный момент круглого/кольцевого сечения = 2·I — учебник сопромата.
    assert section.polar_moment_of_inertia_mm4 == pytest.approx(2.0 * expected_i, rel=1e-9)


def test_hollow_section_rejects_inner_not_smaller_than_outer():
    with pytest.raises(ShaftBeamModelError):
        HollowCircularSection(outer_diameter_mm=50.0, inner_diameter_mm=50.0)
    with pytest.raises(ShaftBeamModelError):
        HollowCircularSection(outer_diameter_mm=50.0, inner_diameter_mm=60.0)


def test_euler_bernoulli_applicability_threshold():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    ok_long, _ = section.euler_bernoulli_applicable(span_mm=2000.0)   # L/D=20
    ok_short, _ = section.euler_bernoulli_applicable(span_mm=500.0)   # L/D=5
    assert ok_long is True
    assert ok_short is False


# ---------------------------------------------------------------------------
# Независимая проверка коммита c24d42b, раздел 5: ЧИСЛЕННАЯ (не L/D-фильтр)
# оценка вклада сдвиговой деформации в прогиб.
# ---------------------------------------------------------------------------

def test_shear_deflection_estimate_matches_closed_form_formulas():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    span, p, e, g = 1800.0, 6000.0, 210000.0, 80000.0
    result = central_point_load_shear_deflection_estimate(span, p, section, e, g, shear_correction_factor=0.5)
    expected_bending = p * span ** 3 / (48.0 * e * section.moment_of_inertia_mm4)
    expected_shear = p * span / (4.0 * 0.5 * g * section.area_mm2)
    assert result.bending_deflection_mm == pytest.approx(expected_bending, rel=1e-9)
    assert result.shear_deflection_mm == pytest.approx(expected_shear, rel=1e-9)
    assert result.shear_to_bending_ratio == pytest.approx(expected_shear / expected_bending, rel=1e-9)


def test_shear_deflection_estimate_matches_numeric_deflection_solver_for_bending_part():
    # Сверка δ_bending этой закрытой формулы с УЖЕ ЧИСЛЕННО посчитанным
    # прогибом того же случая через solve_deflection() (два независимых
    # пути должны дать одно и то же число для центральной силы).
    span, p, e = 1800.0, 6000.0, 210000.0
    section = HollowCircularSection(outer_diameter_mm=114.0, inner_diameter_mm=94.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    sol = solve_shear_moment(case, PLANE_VERTICAL)
    profile = SteppedShaftProfile.uniform(span, section, e)
    sol = solve_deflection(sol, profile)
    numeric_mid_deflection = abs(sol.deflection_mm(span / 2.0))
    estimate = central_point_load_shear_deflection_estimate(span, p, section, e, 80000.0)
    assert estimate.bending_deflection_mm == pytest.approx(numeric_mid_deflection, rel=1e-6)


def test_shear_deflection_estimate_ratio_grows_for_shorter_stubbier_spans():
    # Короче пролёт при том же сечении → доля сдвига в суммарном прогибе
    # РАСТЁТ (δ_shear ~ L, δ_bending ~ L³ → ratio ~ 1/L²) — качественная
    # проверка направления зависимости, а не конкретного порога.
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    long_span = central_point_load_shear_deflection_estimate(3000.0, 5000.0, section, 210000.0, 80000.0)
    short_span = central_point_load_shear_deflection_estimate(300.0, 5000.0, section, 210000.0, 80000.0)
    assert short_span.shear_to_bending_ratio > long_span.shear_to_bending_ratio


def test_shear_deflection_estimate_rejects_nonpositive_span_or_moduli():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    with pytest.raises(ShaftBeamModelError):
        central_point_load_shear_deflection_estimate(0.0, 1000.0, section, 210000.0, 80000.0)
    with pytest.raises(ShaftBeamModelError):
        central_point_load_shear_deflection_estimate(1000.0, 1000.0, section, -1.0, 80000.0)
    with pytest.raises(ShaftBeamModelError):
        central_point_load_shear_deflection_estimate(1000.0, 1000.0, section, 210000.0, 80000.0, shear_correction_factor=0.0)


# --- реакции: сверка с закрытой формулой -----------------------------------

def test_reactions_point_load_at_midspan_are_equal_halves():
    """Классика: точечная сила P в середине пролёта L → R1=R2=P/2."""
    span = 2000.0
    p = 1000.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    reactions = solve_reactions(case, PLANE_VERTICAL)
    assert reactions.support_a_n == pytest.approx(p / 2.0, rel=1e-9)
    assert reactions.support_b_n == pytest.approx(p / 2.0, rel=1e-9)


def test_reactions_eccentric_point_load_matches_lever_formula():
    """P на расстоянии a от левой опоры, b от правой (a+b=L): R1=P·b/L, R2=P·a/L."""
    span = 3000.0
    a, b = 1200.0, span - 1200.0
    p = 5000.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0), ShaftSupport(span, axially_fixed=True)],
        point_loads=[PointLoad(a, p, PLANE_VERTICAL)],
    )
    reactions = solve_reactions(case, PLANE_VERTICAL)
    assert reactions.support_a_n == pytest.approx(p * b / span, rel=1e-9)
    assert reactions.support_b_n == pytest.approx(p * a / span, rel=1e-9)


def test_reactions_udl_over_full_span_are_equal_halves():
    """Равномерная нагрузка w по всему пролёту L → R1=R2=w·L/2."""
    span = 2500.0
    w = 2.0  # Н/мм
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        distributed_loads=[DistributedLoad(0.0, span, w, PLANE_VERTICAL)],
    )
    reactions = solve_reactions(case, PLANE_VERTICAL)
    assert reactions.support_a_n == pytest.approx(w * span / 2.0, rel=1e-9)
    assert reactions.support_b_n == pytest.approx(w * span / 2.0, rel=1e-9)


def test_reactions_reject_more_or_fewer_than_two_supports():
    with pytest.raises(ShaftBeamModelError):
        BeamLoadCase(total_length_mm=1000.0, supports=[ShaftSupport(0.0)])
    with pytest.raises(ShaftBeamModelError):
        BeamLoadCase(
            total_length_mm=1000.0,
            supports=[ShaftSupport(0.0), ShaftSupport(500.0), ShaftSupport(1000.0)],
        )


def test_axial_load_without_axially_fixed_support_raises_not_defaults_to_zero():
    case = BeamLoadCase(
        total_length_mm=1000.0,
        supports=[ShaftSupport(0.0), ShaftSupport(1000.0)],   # ни одна не axially_fixed
        axial_loads=[AxialLoad(500.0)],
    )
    with pytest.raises(ShaftBeamModelError):
        solve_reactions(case, PLANE_VERTICAL)


# --- момент/перерезывающая сила: сверка с закрытой формулой ----------------

def test_moment_point_load_at_midspan_matches_pl_over_4():
    span = 2000.0
    p = 1000.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    m_max = solution.moment(span / 2.0)
    assert m_max == pytest.approx(p * span / 4.0, rel=1e-9)
    # На опорах момент = 0 (шарнир, без свеса).
    assert solution.moment(0.0) == pytest.approx(0.0, abs=1e-9)
    assert solution.moment(span) == pytest.approx(0.0, abs=1e-6)


def test_moment_udl_over_full_span_matches_wl2_over_8():
    span = 2400.0
    w = 3.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        distributed_loads=[DistributedLoad(0.0, span, w, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    m_max = solution.moment(span / 2.0)
    assert m_max == pytest.approx(w * span ** 2 / 8.0, rel=1e-6)


def test_moment_eccentric_point_load_matches_pab_over_l():
    span = 3000.0
    a, b = 1200.0, 1800.0
    p = 5000.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0), ShaftSupport(span, axially_fixed=True)],
        point_loads=[PointLoad(a, p, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    m_at_load = solution.moment(a)
    assert m_at_load == pytest.approx(p * a * b / span, rel=1e-9)


def test_shear_jumps_by_point_load_magnitude():
    span = 2000.0
    p = 800.0
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    v_before = solution.shear(span / 2.0 - 1.0)
    v_after = solution.shear(span / 2.0 + 1.0)
    assert v_before - v_after == pytest.approx(p, rel=1e-6)


# --- прогиб: сверка с закрытой формулой -------------------------------------

def test_deflection_point_load_at_midspan_matches_pl3_over_48ei():
    span = 2000.0
    p = 1000.0
    e_mpa = 210000.0  # сталь, МПа
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    solution = solve_deflection(solution, SteppedShaftProfile.uniform(span, section, e_mpa))
    ei = e_mpa * section.moment_of_inertia_mm4
    expected = p * span ** 3 / (48.0 * ei)
    y_mid = solution.deflection_mm(span / 2.0)
    # Знак: нагрузка вниз (положительная) должна давать прогиб В ТУ ЖЕ сторону.
    assert abs(y_mid) == pytest.approx(expected, rel=1e-6)
    # На опорах прогиб строго 0 — граничные условия решателя.
    assert solution.deflection_mm(0.0) == pytest.approx(0.0, abs=1e-9)
    assert solution.deflection_mm(span) == pytest.approx(0.0, abs=1e-6)


def test_deflection_udl_matches_5wl4_over_384ei():
    span = 2400.0
    w = 3.0
    e_mpa = 210000.0
    section = HollowCircularSection(outer_diameter_mm=120.0, inner_diameter_mm=100.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        distributed_loads=[DistributedLoad(0.0, span, w, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    solution = solve_deflection(solution, SteppedShaftProfile.uniform(span, section, e_mpa))
    ei = e_mpa * section.moment_of_inertia_mm4
    expected = 5.0 * w * span ** 4 / (384.0 * ei)
    y_mid = solution.deflection_mm(span / 2.0)
    assert abs(y_mid) == pytest.approx(expected, rel=1e-4)


# --- крутящий момент: путь отдельный от опор --------------------------------

def test_torque_diagram_is_independent_of_supports_and_accumulates():
    torques = [
        AppliedTorque(position_mm=500.0, torque_nm=200.0, label="привод"),
        AppliedTorque(position_mm=2000.0, torque_nm=-200.0, label="сопротивление продукта"),
    ]
    assert torque_diagram(torques, 100.0) == 0.0
    assert torque_diagram(torques, 1000.0) == pytest.approx(200.0)
    assert torque_diagram(torques, 2500.0) == pytest.approx(0.0)


def test_torque_equilibrium_residual_flags_unbalanced_scheme():
    balanced = [AppliedTorque(0.0, 100.0), AppliedTorque(1000.0, -100.0)]
    unbalanced = [AppliedTorque(0.0, 100.0), AppliedTorque(1000.0, -50.0)]
    assert torque_equilibrium_residual(balanced) == pytest.approx(0.0)
    assert torque_equilibrium_residual(unbalanced) == pytest.approx(50.0)


# --- напряжения: Мизес отдельно от Треска ------------------------------------

def test_combined_von_mises_uses_factor_3_not_4():
    sigma = 100.0
    tau = 40.0
    mises = combined_von_mises_stress_mpa(sigma, tau)
    tresca_like = math.sqrt(sigma ** 2 + 4.0 * tau ** 2)
    assert mises == pytest.approx(math.sqrt(sigma ** 2 + 3.0 * tau ** 2), rel=1e-9)
    assert mises != pytest.approx(tresca_like, rel=1e-6)


def test_bending_and_torsion_stress_formulas():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    m_nmm = 5_000_000.0
    t_nmm = 3_000_000.0
    sigma = bending_stress_mpa(m_nmm, section)
    tau = torsional_shear_stress_mpa(t_nmm, section)
    assert sigma == pytest.approx(m_nmm / section.section_modulus_bending_mm3, rel=1e-12)
    assert tau == pytest.approx(t_nmm / section.section_modulus_torsion_mm3, rel=1e-12)


# --- критическая частота и устойчивость: применимость, не готовое число ----

def test_critical_speed_without_added_mass_is_labeled_bare_shaft():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    rpm, note = critical_speed_rpm(section, span_mm=2515.0, e_mpa=210000.0, density_kg_m3=7850.0)
    assert rpm > 0
    assert "голого вала" in note.lower()


def test_critical_speed_with_added_mass_uses_dunkerley_and_is_lower_than_bare():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    rpm_bare, _ = critical_speed_rpm(section, 2515.0, 210000.0, 7850.0)
    rpm_with_mass, note = critical_speed_rpm(section, 2515.0, 210000.0, 7850.0, added_mass_kg=50.0)
    assert rpm_with_mass < rpm_bare
    assert "донкерлея" in note.lower()


def test_buckling_not_applicable_without_compressive_load():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    result = buckling_applicability(section, effective_length_mm=2515.0, e_mpa=210000.0, axial_compressive_n=None)
    assert result.applicable is False
    result_tension = buckling_applicability(section, 2515.0, 210000.0, axial_compressive_n=-500.0)
    assert result_tension.applicable is False


def test_buckling_applicable_with_compression_reports_euler_load():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    result = buckling_applicability(section, effective_length_mm=2515.0, e_mpa=210000.0, axial_compressive_n=5000.0)
    assert result.applicable is True
    i_mm4 = section.moment_of_inertia_mm4
    expected_pcr = math.pi ** 2 * 210000.0 * i_mm4 / (2515.0 ** 2)
    assert result.euler_critical_load_n == pytest.approx(expected_pcr, rel=1e-9)


# --- зазор: реальные слагаемые, не произвольное отношение --------------------

def test_clearance_check_subtracts_real_terms_not_arbitrary_ratio():
    result = clearance_check(
        housing_inner_diameter_mm=210.0, screw_outer_diameter_mm=200.0,
        shaft_deflection_mm=1.0, runout_mm=0.5, manufacturing_tolerance_mm=0.3, wear_allowance_mm=1.0,
    )
    assert result.nominal_radial_clearance_mm == pytest.approx(5.0)
    assert result.available_clearance_mm == pytest.approx(5.0 - 1.0 - 0.5 - 0.3 - 1.0)
    assert result.ok is True


def test_clearance_check_rejects_housing_smaller_than_screw():
    with pytest.raises(ShaftBeamModelError):
        clearance_check(housing_inner_diameter_mm=100.0, screw_outer_diameter_mm=120.0, shaft_deflection_mm=0.0)


# ---------------------------------------------------------------------------
# Ступенчатый вал: свои E/I (и G/J для кручения) на каждом участке — Codex-
# замечание (продолжение, 18.09.2026, п.1). Раньше solve_deflection()
# принимала одно e_mpa/section на весь пролёт.
# ---------------------------------------------------------------------------

def test_section_segment_rejects_gap_and_overlap_in_profile():
    sec = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    with pytest.raises(ShaftBeamModelError):  # разрыв между 400 и 400.1
        SteppedShaftProfile(total_length_mm=1000.0, segments=[
            SectionSegment(0.0, 400.0, sec, 210000.0),
            SectionSegment(400.1, 1000.0, sec, 210000.0),
        ])
    with pytest.raises(ShaftBeamModelError):  # наложение
        SteppedShaftProfile(total_length_mm=1000.0, segments=[
            SectionSegment(0.0, 500.0, sec, 210000.0),
            SectionSegment(400.0, 1000.0, sec, 210000.0),
        ])
    with pytest.raises(ShaftBeamModelError):  # не начинается с 0
        SteppedShaftProfile(total_length_mm=1000.0, segments=[SectionSegment(10.0, 1000.0, sec, 210000.0)])
    with pytest.raises(ShaftBeamModelError):  # не доходит до total_length_mm
        SteppedShaftProfile(total_length_mm=1000.0, segments=[SectionSegment(0.0, 900.0, sec, 210000.0)])


def test_solve_deflection_rejects_profile_length_mismatch():
    span = 2000.0
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, 1000.0, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    wrong_profile = SteppedShaftProfile.uniform(span - 1.0, section, 210000.0)
    with pytest.raises(ShaftBeamModelError):
        solve_deflection(solution, wrong_profile)


def test_solve_deflection_rejects_non_profile_argument():
    span = 2000.0
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, 1000.0, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    with pytest.raises(ShaftBeamModelError):
        solve_deflection(solution, 210000.0)   # старая сигнатура (e_mpa напрямую) — больше не поддерживается


def test_stepped_profile_split_at_identical_section_matches_uniform_beam():
    """
    Балка, представленная ДВУМЯ соседними участками с ОДИНАКОВЫМ E/сечением,
    физически совпадает с однородной балкой — прогиб должен совпасть с
    закрытой формулой P·L³/(48·EI), а разбиение на участки — не повлиять.
    """
    span = 2000.0
    p = 1000.0
    e_mpa = 210000.0
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    solution = solve_shear_moment(case, PLANE_VERTICAL)
    # Разбиение РОВНО в точке приложения нагрузки (совпадающая точка разрыва) —
    # намеренно жёсткий случай для объединения множеств точек разрыва.
    profile = SteppedShaftProfile(total_length_mm=span, segments=[
        SectionSegment(0.0, span / 2.0, section, e_mpa),
        SectionSegment(span / 2.0, span, section, e_mpa),
    ])
    solution = solve_deflection(solution, profile)
    ei = e_mpa * section.moment_of_inertia_mm4
    expected = p * span ** 3 / (48.0 * ei)
    assert abs(solution.deflection_mm(span / 2.0)) == pytest.approx(expected, rel=1e-6)
    assert solution.deflection_mm(0.0) == pytest.approx(0.0, abs=1e-9)
    assert solution.deflection_mm(span) == pytest.approx(0.0, abs=1e-6)


def test_stepped_shaft_deflection_is_bounded_by_uniform_soft_and_stiff_cases():
    """
    Ступенчатый вал: жёсткие (большой D) концевые участки под подшипники +
    мягкий (малый D) средний рабочий участок, нагрузка в середине. Прогиб
    РЕАЛЬНОГО ступенчатого вала обязан лежать МЕЖДУ прогибом полностью
    жёсткого и полностью мягкого однородного вала той же длины — это прямое
    физическое следствие того, что часть пролёта жёстче, часть — мягче
    (не зависит от точной формулы стыковки, поэтому надёжная проверка).
    """
    span = 2000.0
    p = 1000.0
    e_mpa = 210000.0
    stiff = HollowCircularSection(outer_diameter_mm=140.0, inner_diameter_mm=100.0)
    soft = HollowCircularSection(outer_diameter_mm=90.0, inner_diameter_mm=76.0)
    a = 400.0

    def deflection_for_profile(profile: SteppedShaftProfile) -> float:
        case = BeamLoadCase(
            total_length_mm=span,
            supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
            point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
        )
        solution = solve_shear_moment(case, PLANE_VERTICAL)
        solution = solve_deflection(solution, profile)
        return abs(solution.deflection_mm(span / 2.0))

    y_all_stiff = deflection_for_profile(SteppedShaftProfile.uniform(span, stiff, e_mpa))
    y_all_soft = deflection_for_profile(SteppedShaftProfile.uniform(span, soft, e_mpa))
    y_stepped = deflection_for_profile(SteppedShaftProfile(total_length_mm=span, segments=[
        SectionSegment(0.0, a, stiff, e_mpa),
        SectionSegment(a, span - a, soft, e_mpa),
        SectionSegment(span - a, span, stiff, e_mpa),
    ]))
    assert y_all_stiff < y_stepped < y_all_soft


# --- угол закручивания на ступенчатом профиле (G/J по участкам) ------------

def test_twist_angle_matches_closed_form_tl_over_gj_uniform_shaft():
    length = 1000.0
    g_mpa = 80000.0
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    torques = [AppliedTorque(0.0, 200.0, label="привод"), AppliedTorque(length, -200.0, label="сопротивление")]
    profile = SteppedShaftProfile.uniform(length, section, e_mpa=210000.0, g_mpa=g_mpa)
    twist = solve_twist_angle(torques, profile, reference_position_mm=0.0)
    gj = g_mpa * section.polar_moment_of_inertia_mm4
    expected = 200.0 * 1000.0 * length / gj   # T[Н·мм]·L / GJ
    assert twist.twist_angle_rad(length) == pytest.approx(expected, rel=1e-9)
    assert twist.twist_angle_rad(0.0) == pytest.approx(0.0, abs=1e-12)


def test_twist_angle_on_stepped_shaft_sums_series_compliance():
    """Два участка под одним и тем же T — угол = сумма T·Li/(GJ)_i (пружины кручения последовательно)."""
    length = 1000.0
    split = 400.0
    torques = [AppliedTorque(0.0, 200.0), AppliedTorque(length, -200.0)]
    sec1 = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    sec2 = HollowCircularSection(outer_diameter_mm=80.0, inner_diameter_mm=60.0)
    g1, g2 = 80000.0, 79000.0
    profile = SteppedShaftProfile(total_length_mm=length, segments=[
        SectionSegment(0.0, split, sec1, e_mpa=210000.0, g_mpa=g1),
        SectionSegment(split, length, sec2, e_mpa=210000.0, g_mpa=g2),
    ])
    twist = solve_twist_angle(torques, profile)
    t_nmm = 200.0 * 1000.0
    expected = t_nmm * split / (g1 * sec1.polar_moment_of_inertia_mm4) + \
        t_nmm * (length - split) / (g2 * sec2.polar_moment_of_inertia_mm4)
    assert twist.twist_angle_rad(length) == pytest.approx(expected, rel=1e-9)


def test_twist_angle_reference_point_and_sign():
    length = 1000.0
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    torques = [AppliedTorque(0.0, 200.0), AppliedTorque(length, -200.0)]
    profile = SteppedShaftProfile.uniform(length, section, e_mpa=210000.0, g_mpa=80000.0)
    twist = solve_twist_angle(torques, profile, reference_position_mm=length)
    # Отсчёт от правого конца — угол В НАЧАЛЕ должен быть противоположен по знаку.
    forward = solve_twist_angle(torques, profile, reference_position_mm=0.0)
    assert twist.twist_angle_rad(0.0) == pytest.approx(-forward.twist_angle_rad(length), rel=1e-9)


def test_solve_twist_angle_requires_shear_modulus_on_every_segment():
    section = HollowCircularSection(outer_diameter_mm=100.0, inner_diameter_mm=80.0)
    profile = SteppedShaftProfile.uniform(1000.0, section, e_mpa=210000.0)  # без g_mpa
    with pytest.raises(ShaftBeamModelError):
        solve_twist_angle([AppliedTorque(0.0, 100.0)], profile)

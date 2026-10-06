# -*- coding: utf-8 -*-
"""
Проверка общего 3D-решателя рамы (core/frame_model.py, разделы 3-4 доп.
задания) на ЗАКРЫТЫХ ФОРМУЛАХ сопромата и перекрёстно с независимым
решателем core/shaft_beam_model.py. Полностью синтетические данные.
"""

import dataclasses
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.frame_model import (
    FrameModelError, FrameNode, FrameMember, Support, SectionProperties, NodalLoad, FrameModel,
)
from calculator.core.load_transfer import LoadCase, LoadCaseSet, LoadVector, Point3D
from calculator.core.shaft_beam_model import (
    HollowCircularSection, ShaftSupport, PointLoad, BeamLoadCase,
    solve_shear_moment, solve_deflection, SteppedShaftProfile, PLANE_VERTICAL,
)

E_MPA = 210000.0
G_MPA = 80000.0


def _section(outer=100.0, inner=80.0) -> SectionProperties:
    hc = HollowCircularSection(outer_diameter_mm=outer, inner_diameter_mm=inner)
    return SectionProperties(
        e_mpa=E_MPA, g_mpa=G_MPA, area_mm2=hc.area_mm2,
        iy_mm4=hc.moment_of_inertia_mm4, iz_mm4=hc.moment_of_inertia_mm4,
        j_mm4=hc.polar_moment_of_inertia_mm4, source="synthetic-test",
    )


# --- консоль (одна заделка), сверка с закрытыми формулами -------------------

def _cantilever(length_mm: float):
    section = _section()
    nodes = [
        FrameNode("A", Point3D(0.0, 0.0, 0.0)),
        FrameNode("B", Point3D(length_mm, 0.0, 0.0)),
    ]
    members = [FrameMember("m1", "A", "B", section)]
    supports = [Support.fixed("A")]
    return nodes, members, supports, section


def test_cantilever_tip_force_y_matches_pl3_3ei_and_pl2_2ei():
    length = 2000.0
    p = 1000.0
    nodes, members, supports, section = _cantilever(length)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=p)])
    sol = model.solve()
    ei = E_MPA * section.iz_mm4
    expected_v = p * length ** 3 / (3.0 * ei)
    expected_theta = p * length ** 2 / (2.0 * ei)
    assert sol.displacement_at("B", "uy") == pytest.approx(expected_v, rel=1e-9)
    assert sol.displacement_at("B", "rz") == pytest.approx(expected_theta, rel=1e-9)
    assert sol.reaction_at("A", "uy") == pytest.approx(-p, rel=1e-9)


def test_cantilever_tip_force_z_matches_closed_form_other_plane():
    length = 1500.0
    p = 800.0
    nodes, members, supports, section = _cantilever(length)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fz_n=p)])
    sol = model.solve()
    ei = E_MPA * section.iy_mm4
    expected_w = p * length ** 3 / (3.0 * ei)
    assert sol.displacement_at("B", "uz") == pytest.approx(expected_w, rel=1e-9)


def test_cantilever_axial_force_matches_fl_over_ea():
    length = 1000.0
    p = 5000.0
    nodes, members, supports, section = _cantilever(length)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fx_n=p)])
    sol = model.solve()
    expected_u = p * length / (E_MPA * section.area_mm2)
    assert sol.displacement_at("B", "ux") == pytest.approx(expected_u, rel=1e-9)
    assert sol.reaction_at("A", "ux") == pytest.approx(-p, rel=1e-9)


def test_cantilever_tip_torque_matches_tl_over_gj():
    length = 1200.0
    t = 300000.0  # Н·мм
    nodes, members, supports, section = _cantilever(length)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", mx_nmm=t)])
    sol = model.solve()
    expected_phi = t * length / (G_MPA * section.j_mm4)
    assert sol.displacement_at("B", "rx") == pytest.approx(expected_phi, rel=1e-9)
    assert sol.reaction_at("A", "rx") == pytest.approx(-t, rel=1e-9)


def test_equilibrium_residual_is_near_zero_for_cantilever():
    nodes, members, supports, section = _cantilever(2000.0)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=1000.0, mz_nmm=50000.0)])
    sol = model.solve()
    residual = sol.equilibrium_residual()
    for key, value in residual.items():
        assert abs(value) < 1e-6, f"{key}: {value}"


# --- цепочка элементов = балка на двух опорах: сверка с shaft_beam_model ----

def test_simply_supported_chain_matches_shaft_beam_model_midspan_deflection():
    span = 2000.0
    p = 1000.0
    section = _section()

    nodes = [
        FrameNode("A", Point3D(0.0, 0.0, 0.0)),
        FrameNode("C", Point3D(span / 2.0, 0.0, 0.0)),
        FrameNode("B", Point3D(span, 0.0, 0.0)),
    ]
    members = [
        FrameMember("m1", "A", "C", section),
        FrameMember("m2", "C", "B", section),
    ]
    # Шарнир в A + доп. запрет поворота ВОКРУГ ОСИ ВАЛА (rx) — без него схема
    # (пространственная, а не плоская) остаётся механизмом по кручению: ни
    # одна опора не сопротивляется свободному вращению всей цепочки вокруг
    # собственной оси (нет ни момента, ни ограничения rx нигде) — это
    # РЕАЛЬНЫЙ, физически корректный механизм (см. test_mechanism_without_
    # enough_supports_raises_not_nan), не связанный с изгибом, который здесь
    # проверяется; запрет rx в одной точке убирает эту постороннюю степень
    # свободы, не влияя на изгибные uy/реакции (изгиб и кручение в этой
    # модели механически независимы — общих членов жёсткости нет).
    supports = [
        Support(node_id="A", restrained=(True, True, True, True, False, False), label="шарнир+запрет проворота"),
        Support.roller("B", free_translation="ux"),
    ]
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("C", fy_n=-p)])
    sol = model.solve()
    frame_deflection = abs(sol.displacement_at("C", "uy"))

    # Независимый решатель (core/shaft_beam_model.py) для ТОЙ ЖЕ классической задачи.
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[ShaftSupport(0.0, axially_fixed=True), ShaftSupport(span)],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
    )
    beam_solution = solve_shear_moment(case, PLANE_VERTICAL)
    beam_solution = solve_deflection(beam_solution, SteppedShaftProfile.uniform(span, HollowCircularSection(100.0, 80.0), E_MPA))
    beam_deflection = abs(beam_solution.deflection_mm(span / 2.0))

    assert frame_deflection == pytest.approx(beam_deflection, rel=1e-6)
    # Тоже сверим реакции опор (симметричная схема → по P/2 на каждой).
    assert abs(sol.reaction_at("A", "uy")) == pytest.approx(p / 2.0, rel=1e-6)
    assert abs(sol.reaction_at("B", "uy")) == pytest.approx(p / 2.0, rel=1e-6)


# --- статически неопределимая схема: "propped cantilever" -------------------

def test_propped_cantilever_matches_textbook_indeterminate_solution():
    """
    Заделка в A, каток (опора только по Y) в B, сила P в середине пролёта C.
    Табличное решение (см. докстринг модуля/любой справочник по статически
    неопределимым балкам): R_B=5P/16, R_A=11P/16, |M_A|=3PL/16. Это ПРЯМАЯ
    проверка того, что общий решатель метода перемещений корректно работает
    для статически НЕОПРЕДЕЛИМОЙ схемы (лишняя связь сверх статически
    определимой), не только для определимой (см. тест выше).
    """
    span = 2000.0
    p = 1000.0
    section = _section()

    nodes = [
        FrameNode("A", Point3D(0.0, 0.0, 0.0)),
        FrameNode("C", Point3D(span / 2.0, 0.0, 0.0)),
        FrameNode("B", Point3D(span, 0.0, 0.0)),
    ]
    members = [
        FrameMember("m1", "A", "C", section),
        FrameMember("m2", "C", "B", section),
    ]
    supports = [Support.fixed("A"), Support.roller("B", free_translation="ux")]
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("C", fy_n=-p)])
    sol = model.solve()

    r_b = sol.reaction_at("B", "uy")
    r_a = sol.reaction_at("A", "uy")
    m_a = sol.reaction_at("A", "rz")

    assert abs(r_b) == pytest.approx(5.0 * p / 16.0, rel=1e-6)
    assert abs(r_a) == pytest.approx(11.0 * p / 16.0, rel=1e-6)
    assert abs(m_a) == pytest.approx(3.0 * p * span / 16.0, rel=1e-6)
    # Равновесие по вертикали: реакции должны уравновесить приложенную силу.
    assert abs(r_a) + math.copysign(0, 0) >= 0  # sanity: no-op, real check below
    assert (r_a + r_b) == pytest.approx(p, rel=1e-6) or (r_a + r_b) == pytest.approx(-p, rel=1e-6)

    residual = sol.equilibrium_residual()
    for key, value in residual.items():
        assert abs(value) < 1e-6, f"{key}: {value}"


# --- валидация входных данных ------------------------------------------------

def test_duplicate_node_ids_rejected():
    section = _section()
    with pytest.raises(FrameModelError):
        FrameModel(
            nodes=[FrameNode("A", Point3D(0, 0, 0)), FrameNode("A", Point3D(1, 0, 0))],
            members=[], supports=[],
        )


def test_member_referencing_unknown_node_rejected():
    section = _section()
    with pytest.raises(FrameModelError):
        FrameModel(
            nodes=[FrameNode("A", Point3D(0, 0, 0)), FrameNode("B", Point3D(1000, 0, 0))],
            members=[FrameMember("m1", "A", "X", section)],
            supports=[Support.fixed("A")],
        )


def test_mechanism_without_enough_supports_raises_not_nan():
    section = _section()
    nodes = [FrameNode("A", Point3D(0, 0, 0)), FrameNode("B", Point3D(1000, 0, 0))]
    members = [FrameMember("m1", "A", "B", section)]
    # Только шарнир в A (3 DOF), B полностью свободен — механизм (нет полной заделки нигде).
    supports = [Support.pinned("A")]
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=100.0)])
    with pytest.raises(FrameModelError):
        model.solve()


def test_support_requires_at_least_one_restrained_dof():
    with pytest.raises(FrameModelError):
        Support(node_id="A", restrained=(False,) * 6)


def test_known_limitations_documents_nodal_load_only_assumption():
    section = _section()
    nodes, members, supports, _ = _cantilever(1000.0)
    model = FrameModel(nodes, members, supports)
    limitations = model.known_limitations()
    assert any("узл" in text.lower() for text in limitations)


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P1»): перенос нагрузки
# из core/load_transfer.py в NodalLoad не должен терять источник/режим/
# ревизию/fingerprint.
# ---------------------------------------------------------------------------

def test_nodal_load_from_load_vector_preserves_provenance():
    vector = LoadVector(
        node_ref="опора_A", point=Point3D(0.0, 0.0, 0.0), fx_n=0.0, fy_n=0.0, fz_n=-500.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING,
        source="shaft_beam_model.solve_reactions#support_a", label="реакция_A",
        product_revision="rev1", input_fingerprint="fp1",
    )
    nodal = NodalLoad.from_load_vector("H_LOAD_A", vector)
    assert nodal.node_id == "H_LOAD_A"
    assert nodal.fz_n == pytest.approx(-500.0)
    assert nodal.source == "shaft_beam_model.solve_reactions#support_a"
    assert nodal.load_cases == (LoadCase.OPERATING,)
    assert nodal.product_revision == "rev1"
    assert nodal.input_fingerprint == "fp1"
    assert nodal.label == "реакция_A"


def test_nodal_load_from_load_vector_still_solves_correctly_in_a_model():
    length = 1000.0
    p = 500.0
    section = _section()
    nodes, members, supports, _ = _cantilever(length)
    vector = LoadVector(
        node_ref="B", point=Point3D(length, 0.0, 0.0), fx_n=0.0, fy_n=p, fz_n=0.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING, source="synthetic-test",
    )
    model = FrameModel(nodes, members, supports, loads=[NodalLoad.from_load_vector("B", vector)])
    sol = model.solve()
    ei = E_MPA * section.iz_mm4
    expected_v = p * length ** 3 / (3.0 * ei)
    assert sol.displacement_at("B", "uy") == pytest.approx(expected_v, rel=1e-9)


def test_nodal_load_from_resultant_preserves_provenance():
    s = LoadCaseSet()
    s.add(LoadVector(
        node_ref="A", point=Point3D(0.0, 0.0, 0.0), fx_n=0.0, fy_n=0.0, fz_n=-200.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.SELF_WEIGHT, source="src1",
        product_revision="rev1", input_fingerprint="fp1",
    ))
    resultant = s.resultant_at(Point3D(0.0, 0.0, 0.0), cases=[LoadCase.SELF_WEIGHT])
    nodal = NodalLoad.from_resultant("A", resultant)
    assert nodal.fz_n == pytest.approx(-200.0)
    assert nodal.load_cases == (LoadCase.SELF_WEIGHT,)
    assert nodal.product_revision == "rev1"
    assert nodal.input_fingerprint == "fp1"
    assert nodal.source == "load_transfer.LoadCaseSet.resultant_at"


def test_nodal_load_manual_construction_without_provenance_still_works():
    # Ручное конструирование (как во всех тестах решателя на закрытых
    # формулах) не должно требовать заполнения новых полей происхождения.
    nodal = NodalLoad("B", fy_n=1000.0)
    assert nodal.source == ""
    assert nodal.load_cases == ()


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P0»): свободное тело
# всей модели через ОТДЕЛЬНО протестированный core/load_transfer.py, а не
# через внутреннюю бухгалтерию equilibrium_residual() этого же модуля.
# ---------------------------------------------------------------------------

def test_independent_free_body_check_matches_equilibrium_residual_for_cantilever():
    nodes, members, supports, section = _cantilever(1500.0)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=1000.0, mz_nmm=25000.0)])
    sol = model.solve()
    residual = sol.equilibrium_residual()
    independent = sol.independent_free_body_check(Point3D(0.0, 0.0, 0.0))
    for key in ("fx", "fy", "fz", "mx", "my", "mz"):
        assert independent[key] == pytest.approx(residual[key], abs=1e-6)
        assert abs(independent[key]) < 1e-6


def test_independent_free_body_check_is_reference_point_invariant():
    # Суммарная сила и результирующий момент СИСТЕМЫ В РАВНОВЕСИИ равны 0
    # относительно ЛЮБОЙ точки приведения, не только начала координат.
    nodes, members, supports, section = _cantilever(1500.0)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=1000.0, mz_nmm=25000.0)])
    sol = model.solve()
    for point in (Point3D(0.0, 0.0, 0.0), Point3D(500.0, -200.0, 300.0)):
        check = sol.independent_free_body_check(point)
        for key in ("fx", "fy", "fz", "mx", "my", "mz"):
            assert abs(check[key]) < 1e-6, f"{point}: {key}={check[key]}"


# ---------------------------------------------------------------------------
# Независимая проверка коммита c24d42b, раздел 2: неизменяемый снимок
# нагрузок + проверка ревизии/fingerprint НА ГРАНИЦЕ solve(), плюс проверка
# совпадения точки приложения при построении NodalLoad из LoadVector.
# ---------------------------------------------------------------------------

def test_nodal_load_is_immutable():
    nodal = NodalLoad("B", fy_n=1000.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        nodal.fy_n = -999.0


def test_frame_model_loads_is_an_immutable_snapshot():
    nodes, members, supports, section = _cantilever(1500.0)
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=1000.0)])
    assert isinstance(model.loads, tuple)
    with pytest.raises(AttributeError):
        model.loads.append(NodalLoad("B", fy_n=1.0))


def test_frame_model_rejects_mixed_product_revision_among_nodal_loads():
    # Repro независимой проверки c24d42b: solve() раньше молча принимал
    # NodalLoad с РАЗНЫМИ product_revision одновременно.
    nodes, members, supports, section = _cantilever(1500.0)
    loads = [
        NodalLoad("B", fy_n=500.0, product_revision="rev-old"),
        NodalLoad("B", fx_n=100.0, product_revision="rev-new"),
    ]
    with pytest.raises(FrameModelError):
        FrameModel(nodes, members, supports, loads=loads)


def test_frame_model_rejects_mixed_input_fingerprint_among_nodal_loads():
    nodes, members, supports, section = _cantilever(1500.0)
    loads = [
        NodalLoad("B", fy_n=500.0, input_fingerprint="fp-old"),
        NodalLoad("B", fx_n=100.0, input_fingerprint="fp-new"),
    ]
    with pytest.raises(FrameModelError):
        FrameModel(nodes, members, supports, loads=loads)


def test_frame_model_allows_loads_without_revision_metadata_to_coexist():
    # Нагрузки БЕЗ проставленной ревизии (пустая строка) не блокируют друг
    # друга — иначе все существующие тесты решателя на закрытых формулах
    # (не отслеживающие ревизию) ложно ломались бы.
    nodes, members, supports, section = _cantilever(1500.0)
    loads = [NodalLoad("B", fy_n=500.0), NodalLoad("B", fx_n=100.0)]
    model = FrameModel(nodes, members, supports, loads=loads)
    assert model.solve() is not None


def test_frame_model_allows_single_shared_revision_among_nodal_loads():
    nodes, members, supports, section = _cantilever(1500.0)
    loads = [
        NodalLoad("B", fy_n=500.0, product_revision="rev1", input_fingerprint="fp1"),
        NodalLoad("B", fx_n=100.0, product_revision="rev1", input_fingerprint="fp1"),
    ]
    model = FrameModel(nodes, members, supports, loads=loads)
    assert model.solve() is not None


def test_from_load_vector_rejects_mismatched_expected_point():
    vector = LoadVector(
        node_ref="опора_B", point=Point3D(0.0, 0.0, 0.0), fx_n=0.0, fy_n=-100.0, fz_n=0.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING, source="synthetic-test",
    )
    with pytest.raises(FrameModelError):
        NodalLoad.from_load_vector("B", vector, expected_point=Point3D(1500.0, 0.0, 0.0))


def test_from_load_vector_accepts_matching_expected_point():
    point = Point3D(1500.0, 0.0, 0.0)
    vector = LoadVector(
        node_ref="опора_B", point=point, fx_n=0.0, fy_n=-100.0, fz_n=0.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING, source="synthetic-test",
    )
    nodal = NodalLoad.from_load_vector("B", vector, expected_point=point)
    assert nodal.fy_n == pytest.approx(-100.0)


def test_from_load_vector_without_expected_point_does_not_check_anything():
    # Без expected_point (не передан) проверка не выполняется — обратная
    # совместимость с местами, где координата узла неизвестна вызывающему.
    vector = LoadVector(
        node_ref="опора_B", point=Point3D(999.0, 0.0, 0.0), fx_n=0.0, fy_n=-100.0, fz_n=0.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING, source="synthetic-test",
    )
    nodal = NodalLoad.from_load_vector("B", vector)
    assert nodal.fy_n == pytest.approx(-100.0)


# ---------------------------------------------------------------------------
# Независимая проверка коммита c24d42b, раздел 5: интерполяция перемещений
# ВНУТРИ элемента (не только в узлах) — кубика Эрмита, сверенная с закрытой
# формулой консоли в ОБЕИХ плоскостях изгиба одновременно (косое нагружение).
# ---------------------------------------------------------------------------

def _cantilever_biaxial(length_mm: float, fy_n: float, fz_n: float):
    section = _section()
    nodes = [FrameNode("A", Point3D(0.0, 0.0, 0.0)), FrameNode("B", Point3D(length_mm, 0.0, 0.0))]
    members = [FrameMember("m1", "A", "B", section)]
    supports = [Support.fixed("A")]
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", fy_n=fy_n, fz_n=fz_n)])
    return model.solve(), section


def test_transverse_displacement_matches_nodal_values_at_endpoints():
    length = 1500.0
    sol, section = _cantilever_biaxial(length, fy_n=700.0, fz_n=-900.0)
    dx0, dy0, dz0 = sol.transverse_displacement_along_member("m1", 0.0)
    assert (dx0, dy0, dz0) == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)
    dxL, dyL, dzL = sol.transverse_displacement_along_member("m1", length)
    assert dyL == pytest.approx(sol.displacement_at("B", "uy"), rel=1e-9)
    assert dzL == pytest.approx(sol.displacement_at("B", "uz"), rel=1e-9)


def test_transverse_displacement_matches_closed_form_cantilever_biaxial():
    # v(x) = (P/(6EI))·(3Lx² − x³) — закрытая формула консоли, ОТДЕЛЬНО в
    # каждой из двух плоскостей изгиба под КОСЫМ (fy И fz одновременно)
    # нагружением, чтобы исключить случайное совпадение знаков одной плоскости.
    length = 1500.0
    fy, fz = 700.0, -900.0
    sol, section = _cantilever_biaxial(length, fy_n=fy, fz_n=fz)

    def closed_form(x, p):
        return (p / (6.0 * E_MPA * section.iy_mm4)) * (3.0 * length * x ** 2 - x ** 3)

    for x in (150.0, 300.0, 750.0, 1000.0, 1200.0, 1499.0):
        _, dy, dz = sol.transverse_displacement_along_member("m1", x)
        assert dy == pytest.approx(closed_form(x, fy), rel=1e-9)
        assert dz == pytest.approx(closed_form(x, fz), rel=1e-9)


def test_transverse_displacement_rejects_s_outside_member_length():
    sol, _ = _cantilever_biaxial(1500.0, fy_n=100.0, fz_n=0.0)
    with pytest.raises(FrameModelError):
        sol.transverse_displacement_along_member("m1", 1600.0)
    with pytest.raises(FrameModelError):
        sol.transverse_displacement_along_member("m1", -10.0)


def test_transverse_displacement_can_have_interior_extremum_not_at_a_node():
    # Критическое сечение по длине НЕ обязано совпадать с узлом модели:
    # балка на двух шарнирных опорах (заделка+ролик здесь моделируется как
    # шарнир-шарнир через FrameModel) с моментами на обоих концах — прогиб
    # внутри пролёта не обязан монотонно идти к максимуму В УЗЛЕ.
    length = 2000.0
    section = _section()
    nodes = [FrameNode("A", Point3D(0.0, 0.0, 0.0)), FrameNode("B", Point3D(length, 0.0, 0.0))]
    members = [FrameMember("m1", "A", "B", section)]
    # Шарнирные опоры по перемещениям, свободный поворот изгиба — момент
    # на "B" создаёт S-образный изгиб с экстремумом строго внутри пролёта.
    # rx (кручение вокруг оси элемента) закреплено В ОДНОМ узле (A) —
    # иначе абсолютный поворот вокруг собственной оси элемента без
    # внешнего момента является механизмом (система сопротивляется только
    # ОТНОСИТЕЛЬНОМУ закручиванию, не абсолютному повороту обоих концов).
    supports = [
        Support(node_id="A", restrained=(True, True, True, True, False, False)),
        Support(node_id="B", restrained=(False, True, True, False, False, False)),
    ]
    model = FrameModel(nodes, members, supports, loads=[NodalLoad("B", mz_nmm=5.0e6)])
    sol = model.solve()
    xs = [i * length / 200.0 for i in range(201)]
    values = [sol.transverse_displacement_along_member("m1", x)[1] for x in xs]
    abs_values = [abs(v) for v in values]
    i_max = max(range(len(abs_values)), key=lambda i: abs_values[i])
    # Экстремум по модулю НЕ на одном из двух узлов (i=0 или i=len-1).
    assert 0 < i_max < len(xs) - 1


def test_from_resultant_rejects_mismatched_expected_point():
    s = LoadCaseSet()
    s.add(LoadVector(
        node_ref="A", point=Point3D(0.0, 0.0, 0.0), fx_n=0.0, fy_n=0.0, fz_n=-200.0,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.SELF_WEIGHT, source="src1",
    ))
    resultant = s.resultant_at(Point3D(0.0, 0.0, 0.0), cases=[LoadCase.SELF_WEIGHT])
    with pytest.raises(FrameModelError):
        NodalLoad.from_resultant("A", resultant, expected_point=Point3D(500.0, 0.0, 0.0))

# -*- coding: utf-8 -*-
"""
Проверка совместного расчёта относительного зазора вал/корпус
(core/shaft_housing_clearance.py, независимая проверка коммита 377e33c,
раздел «P0. Посчитать относительный зазор»). Синтетические данные.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.shaft_housing_clearance import (
    ShaftHousingClearanceError, LateralDisplacement, clearance_consumption_from_vectors,
    interpolate_between_supports, shaft_absolute_lateral_displacement_mm,
    SectionClearanceResult, critical_section_clearance, rigid_offset_lateral_displacement,
)


# --- векторная разность перемещений (не сумма модулей) ----------------------

def test_identical_joint_displacements_consume_no_clearance():
    shaft = LateralDisplacement(2.0, 3.0)
    housing = LateralDisplacement(2.0, 3.0)
    assert clearance_consumption_from_vectors(shaft, housing) == pytest.approx(0.0)


def test_opposite_displacements_add_up():
    shaft = LateralDisplacement(2.0, 0.0)
    housing = LateralDisplacement(-2.0, 0.0)
    # Разность = (2-(-2), 0) = (4,0) → модуль 4, НЕ 2+2 "случайно совпавшее"
    # арифметическое сложение по модулю — это разность векторов, но в данном
    # направлении её модуль действительно равен сумме модулей (компоненты
    # коллинеарны и противоположны) — прямое соответствие пункту задания
    # "противоположные складываются".
    assert clearance_consumption_from_vectors(shaft, housing) == pytest.approx(4.0)


def test_orthogonal_displacements_combine_by_pythagoras_not_sum_of_magnitudes():
    shaft = LateralDisplacement(3.0, 0.0)
    housing = LateralDisplacement(0.0, 4.0)
    # Разность = (3-0, 0-4) = (3,-4) → модуль 5 (Пифагор), НЕ 3+4=7.
    result = clearance_consumption_from_vectors(shaft, housing)
    assert result == pytest.approx(5.0)
    assert result != pytest.approx(7.0)


def test_partially_cancelling_displacements_consume_less_than_either_alone():
    shaft = LateralDisplacement(5.0, 0.0)
    housing = LateralDisplacement(3.0, 0.0)  # то же направление, меньшая величина
    result = clearance_consumption_from_vectors(shaft, housing)
    assert result == pytest.approx(2.0)
    assert result < 5.0 and result < 3.0 + 5.0


def test_lateral_displacement_rejects_non_finite():
    with pytest.raises(ShaftHousingClearanceError):
        LateralDisplacement(float("nan"), 0.0)
    with pytest.raises(ShaftHousingClearanceError):
        LateralDisplacement(0.0, True)


# --- линейная интерполяция между опорами ------------------------------------

def test_interpolate_between_supports_matches_endpoints():
    assert interpolate_between_supports(0.0, 0.0, 10.0, 100.0, 20.0) == pytest.approx(10.0)
    assert interpolate_between_supports(100.0, 0.0, 10.0, 100.0, 20.0) == pytest.approx(20.0)


def test_interpolate_between_supports_midpoint():
    assert interpolate_between_supports(50.0, 0.0, 10.0, 100.0, 20.0) == pytest.approx(15.0)


def test_interpolate_between_supports_rejects_extrapolation():
    with pytest.raises(ShaftHousingClearanceError):
        interpolate_between_supports(150.0, 0.0, 10.0, 100.0, 20.0)
    with pytest.raises(ShaftHousingClearanceError):
        interpolate_between_supports(-10.0, 0.0, 10.0, 100.0, 20.0)


def test_interpolate_between_supports_rejects_coincident_positions():
    with pytest.raises(ShaftHousingClearanceError):
        interpolate_between_supports(0.0, 50.0, 10.0, 50.0, 20.0)


# --- абсолютное перемещение оси вала = относительный прогиб + опоры --------

def test_shaft_absolute_displacement_at_support_equals_support_displacement_when_relative_is_zero():
    # На самой опоре относительный прогиб вала (относительно ЕЁ ЖЕ опор) = 0
    # по определению (см. docstring shaft_beam_model.solve_deflection) —
    # значит абсолютное перемещение оси ТАМ равно перемещению самой опоры.
    a = LateralDisplacement(0.0, -1.2)
    b = LateralDisplacement(0.0, -0.8)
    result = shaft_absolute_lateral_displacement_mm(
        0.0, 0.0, a, 1800.0, b, relative_dy_mm=0.0, relative_dz_mm=0.0,
    )
    assert result.dz_mm == pytest.approx(-1.2)


def test_shaft_absolute_displacement_adds_relative_deflection_to_interpolated_support_motion():
    a = LateralDisplacement(0.0, -1.0)
    b = LateralDisplacement(0.0, -1.0)
    # Опоры сместились ОДИНАКОВО (-1.0) — интерполяция между ними тоже -1.0
    # в любой точке; добавляем относительный прогиб самого вала в середине.
    result = shaft_absolute_lateral_displacement_mm(
        900.0, 0.0, a, 1800.0, b, relative_dy_mm=0.0, relative_dz_mm=-0.35,
    )
    assert result.dz_mm == pytest.approx(-1.0 - 0.35)


def test_shaft_absolute_displacement_rejects_extrapolation_beyond_supports():
    a = LateralDisplacement(0.0, 0.0)
    b = LateralDisplacement(0.0, 0.0)
    with pytest.raises(ShaftHousingClearanceError):
        shaft_absolute_lateral_displacement_mm(2000.0, 0.0, a, 1800.0, b)


# --- критическое сечение по длине -------------------------------------------

def test_critical_section_clearance_picks_the_worst_section():
    sections = [
        SectionClearanceResult(
            x_mm=0.0, shaft_absolute=LateralDisplacement(0, -1.0), housing_absolute=LateralDisplacement(0, 0),
            consumed_by_deflection_mm=1.0, label="A",
        ),
        SectionClearanceResult(
            x_mm=900.0, shaft_absolute=LateralDisplacement(0, -3.5), housing_absolute=LateralDisplacement(0, 0),
            consumed_by_deflection_mm=3.5, label="mid",
        ),
        SectionClearanceResult(
            x_mm=1800.0, shaft_absolute=LateralDisplacement(0, -0.5), housing_absolute=LateralDisplacement(0, 0),
            consumed_by_deflection_mm=0.5, label="B",
        ),
    ]
    result = critical_section_clearance(
        sections, housing_inner_diameter_mm=140.0, screw_outer_diameter_mm=114.0,
        runout_mm=0.2, manufacturing_tolerance_mm=0.15, wear_allowance_mm=0.5,
    )
    assert result.governing_section.label == "mid"
    assert result.clearance.available_clearance_mm == pytest.approx(13.0 - 3.5 - 0.2 - 0.15 - 0.5, rel=1e-9)
    assert len(result.all_sections) == 3


def test_critical_section_clearance_rejects_empty_section_list():
    with pytest.raises(ShaftHousingClearanceError):
        critical_section_clearance([], housing_inner_diameter_mm=140.0, screw_outer_diameter_mm=114.0)


# ---------------------------------------------------------------------------
# Независимая проверка коммита c24d42b, раздел 1: кинематика жёсткого
# смещения точки, вынесенной из оси модели — u_точки = u_узла + θ×r,
# БЕЗ имитации жёсткой связи произвольно огромной жёсткостью элемента.
# ---------------------------------------------------------------------------

def test_rigid_offset_zero_offset_reduces_to_node_displacement():
    result = rigid_offset_lateral_displacement(
        node_uy_mm=1.5, node_uz_mm=-2.5, twist_rx_rad=0.01, offset_y_mm=0.0, offset_z_mm=0.0,
    )
    assert result.dy_mm == pytest.approx(1.5)
    assert result.dz_mm == pytest.approx(-2.5)


def test_rigid_offset_zero_twist_reduces_to_node_displacement_regardless_of_offset():
    result = rigid_offset_lateral_displacement(
        node_uy_mm=1.5, node_uz_mm=-2.5, twist_rx_rad=0.0, offset_y_mm=40.0, offset_z_mm=-25.0,
    )
    assert result.dy_mm == pytest.approx(1.5)
    assert result.dz_mm == pytest.approx(-2.5)


def test_rigid_offset_pure_twist_matches_theta_cross_r_formula():
    # θ=(rx,0,0), r=(0, offset_y, offset_z) → θ×r=(0, -rx*offset_z, rx*offset_y).
    rx = 0.02  # рад
    offset_y, offset_z = 10.0, 30.0
    result = rigid_offset_lateral_displacement(
        node_uy_mm=0.0, node_uz_mm=0.0, twist_rx_rad=rx, offset_y_mm=offset_y, offset_z_mm=offset_z,
    )
    assert result.dy_mm == pytest.approx(-rx * offset_z)
    assert result.dz_mm == pytest.approx(rx * offset_y)


def test_rigid_offset_combines_node_translation_and_twist_linearly():
    rx = 0.015
    offset_y, offset_z = -20.0, 5.0
    result = rigid_offset_lateral_displacement(
        node_uy_mm=2.0, node_uz_mm=-1.0, twist_rx_rad=rx, offset_y_mm=offset_y, offset_z_mm=offset_z,
    )
    assert result.dy_mm == pytest.approx(2.0 - rx * offset_z)
    assert result.dz_mm == pytest.approx(-1.0 + rx * offset_y)


def test_rigid_offset_opposite_offsets_give_opposite_extra_displacement():
    rx = 0.01
    plus = rigid_offset_lateral_displacement(0.0, 0.0, rx, offset_y_mm=15.0, offset_z_mm=0.0)
    minus = rigid_offset_lateral_displacement(0.0, 0.0, rx, offset_y_mm=-15.0, offset_z_mm=0.0)
    assert plus.dz_mm == pytest.approx(-minus.dz_mm)


def test_rigid_offset_rejects_non_finite_inputs():
    with pytest.raises(ShaftHousingClearanceError):
        rigid_offset_lateral_displacement(float("nan"), 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ShaftHousingClearanceError):
        rigid_offset_lateral_displacement(0.0, 0.0, 0.0, 0.0, float("inf"))

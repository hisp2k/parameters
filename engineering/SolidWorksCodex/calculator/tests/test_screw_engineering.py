# -*- coding: utf-8 -*-
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from calculator.core.screw_engineering import (
    ScrewEngineeringInput, compute_engineering_core, EngineeringInputError, Abrasiveness,
    STANDARD_MOTOR_KW,
)


def _base_input(**overrides) -> ScrewEngineeringInput:
    defaults = dict(
        productivity_value=5.0,
        productivity_unit="т/ч",
        bulk_density_kg_m3=700.0,
        max_lump_size_mm=15.0,
        is_sorted_material=False,
        abrasiveness=Abrasiveness.MEDIUM,
        working_length_mm=3000.0,
        incline_deg=0.0,
    )
    defaults.update(overrides)
    return ScrewEngineeringInput(**defaults)


def test_baseline_matches_known_order_of_magnitude():
    # Stage 12 черновик и заказ №2377 сходятся на диаметре 200 мм для этого
    # порядка производительности — регрессия на случай будущих правок.
    result = compute_engineering_core(_base_input())
    assert result.diameter_mm == 200
    assert result.motor_selection_ok is True
    assert result.motor_power_kw in STANDARD_MOTOR_KW
    assert result.warnings == []


def test_rejects_zero_density():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(bulk_density_kg_m3=0))


def test_rejects_negative_density():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(bulk_density_kg_m3=-10))


def test_rejects_zero_productivity():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(productivity_value=0))


def test_rejects_negative_productivity():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(productivity_value=-1))


def test_rejects_incline_over_20_degrees():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(incline_deg=25))


def test_forced_step_used_in_auto_diameter_mode():
    """Регрессия на баг №2: forced_step_mm раньше игнорировался при автоподборе диаметра."""
    forced_step = 123.0
    result = compute_engineering_core(_base_input(forced_step_mm=forced_step))
    assert result.step_mm == forced_step


def test_forced_step_used_with_forced_diameter():
    result = compute_engineering_core(_base_input(forced_diameter_mm=250, forced_step_mm=99.0))
    assert result.diameter_mm == 250
    assert result.step_mm == 99.0


def test_inadequate_motor_returns_none_not_a_lie():
    """Регрессия на баг №3: раньше возвращался самый мощный мотор ряда как будто он подошёл."""
    huge = _base_input(productivity_value=100000.0, working_length_mm=50000.0)
    result = compute_engineering_core(huge)
    assert result.motor_selection_ok is False
    assert result.motor_power_kw is None
    assert any("не подобран" in w for w in result.warnings)


def test_forced_diameter_below_minimum_warns_but_does_not_raise():
    result = compute_engineering_core(_base_input(forced_diameter_mm=50))
    assert any("меньше минимально допустимого" in w for w in result.warnings)


def test_unknown_productivity_unit_raises():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(productivity_unit="фунт/час"))


def test_unknown_abrasiveness_raises():
    with pytest.raises(EngineeringInputError):
        compute_engineering_core(_base_input(abrasiveness="экзотическая"))

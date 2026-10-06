# -*- coding: utf-8 -*-
"""
Проверка реальных прочностных функций (раздел 3 задания) на контрольных
примерах, посчитанных вручную по тем же учебным формулам сопромата
(третья теория прочности) — НЕ являются подтверждением реального изделия
Тех-Аэро (см. docstring core/strength_calculations.py), а лишь проверяют,
что код реализует формулу правильно.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from calculator.core.strength_calculations import (
    torque_from_power, shaft_torsion_only_check, shaft_combined_check,
    weld_shear_check, bolt_group_shear_check, StrengthCalculationError,
)


def test_torque_from_power_matches_standard_formula():
    # T[Н*м] = 9550 * P[кВт] / n[об/мин] — контрольный пример: 5.5 кВт при 100 об/мин
    t = torque_from_power(shaft_power_kw=5.5, rotation_speed_rpm=100.0)
    assert math.isclose(t, 9550.0 * 5.5 / 100.0, rel_tol=1e-9)


def test_torque_from_power_rejects_non_positive():
    with pytest.raises(Exception):
        torque_from_power(shaft_power_kw=0, rotation_speed_rpm=100.0)
    with pytest.raises(Exception):
        torque_from_power(shaft_power_kw=5.5, rotation_speed_rpm=0)


def test_shaft_torsion_only_matches_hand_calculation():
    # Ручной расчёт: d=40 мм, T=100 Н*м -> Wp=pi*d^3/16=1.25664e-5 м3,
    # tau = T/Wp = 7.9577 МПа (см. test file docstring верхнего уровня).
    outcome = shaft_torsion_only_check(shaft_diameter_mm=40.0, torque_nm=100.0, material="Ст3", safety_factor=3.0)
    assert math.isclose(outcome.result_value, 7.96, abs_tol=0.01)
    assert outcome.criterion_limit == pytest.approx(235.0 / 3.0, abs=0.01)
    assert outcome.passed is True


def test_shaft_torsion_only_fails_when_overloaded():
    # Огромный крутящий момент на тонком валу должен провалить проверку.
    outcome = shaft_torsion_only_check(shaft_diameter_mm=10.0, torque_nm=5000.0, material="Ст3")
    assert outcome.passed is False


def test_shaft_combined_matches_hand_calculation():
    # Ручной расчёт: d=40 мм, T=100 Н*м, M=200 Н*м -> sigma_экв = 35.59 МПа
    outcome = shaft_combined_check(
        shaft_diameter_mm=40.0, torque_nm=100.0, bending_moment_nm=200.0,
        material="Ст3", safety_factor=2.0,
    )
    assert math.isclose(outcome.result_value, 35.59, abs_tol=0.02)
    assert outcome.criterion_limit == pytest.approx(235.0 / 2.0, abs=0.01)
    assert outcome.passed is True


def test_shaft_combined_requires_bending_moment_explicitly():
    """Раздел 3: функция не должна сама придумывать изгибающий момент."""
    with pytest.raises(StrengthCalculationError):
        shaft_combined_check(shaft_diameter_mm=40.0, torque_nm=100.0, bending_moment_nm=float("nan"))
    with pytest.raises(StrengthCalculationError):
        shaft_combined_check(shaft_diameter_mm=40.0, torque_nm=100.0, bending_moment_nm=-5.0)


def test_shaft_check_rejects_unknown_material():
    with pytest.raises(StrengthCalculationError):
        shaft_torsion_only_check(shaft_diameter_mm=40.0, torque_nm=100.0, material="неизвестная_сталь")


def test_weld_shear_matches_hand_calculation():
    # Ручной расчёт: F=10000 Н, катет=6 мм, длина=100 мм ->
    # толщина=0.7*6=4.2 мм, площадь=420 мм2, tau=10000/420=23.81 МПа.
    outcome = weld_shear_check(load_n=10000.0, weld_leg_mm=6.0, weld_length_mm=100.0)
    assert math.isclose(outcome.result_value, 23.81, abs_tol=0.02)
    assert outcome.passed is True


def test_weld_shear_fails_when_undersized():
    outcome = weld_shear_check(load_n=500000.0, weld_leg_mm=3.0, weld_length_mm=20.0)
    assert outcome.passed is False


def test_bolt_group_shear_matches_hand_calculation():
    # Ручной расчёт: F=20000 Н, 4 болта M12 -> A=pi*12^2/4=113.1 мм2,
    # tau=20000/(4*113.1)=44.21 МПа.
    outcome = bolt_group_shear_check(load_n=20000.0, bolt_count=4, bolt_diameter_mm=12.0)
    assert math.isclose(outcome.result_value, 44.2, abs_tol=0.1)
    assert outcome.passed is True


def test_bolt_group_shear_rejects_non_integer_count():
    with pytest.raises(StrengthCalculationError):
        bolt_group_shear_check(load_n=1000.0, bolt_count=2.5, bolt_diameter_mm=10.0)

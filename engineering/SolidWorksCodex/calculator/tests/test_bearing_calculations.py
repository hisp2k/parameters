# -*- coding: utf-8 -*-
"""
Проверка расчёта подшипников (core/bearing_calculations.py) и связки с
VerificationRecord «не менее» (core/verification.py — устранение
ограничения result<=limit для ресурса L10h).
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.bearing_calculations import (
    BearingCalculationError, BearingLifeOverflowError, LIFE_EXPONENT_BALL, LIFE_EXPONENT_ROLLER,
    resultant_radial_load_n, dynamic_equivalent_load, l10_life_hours, static_capacity_safety_factor,
)
from calculator.core.verification import VerificationRecord, CRITERION_AT_LEAST, CRITERION_AT_MOST


def test_resultant_radial_load_is_vector_sum_of_two_planes():
    result = resultant_radial_load_n(3.0, 4.0)
    assert result == pytest.approx(5.0)  # 3-4-5 треугольник


def test_dynamic_equivalent_load_standard_formula():
    result = dynamic_equivalent_load(radial_load_n=1000.0, axial_load_n=300.0, x_factor=1.0, y_factor=0.5)
    assert result.equivalent_load_n == pytest.approx(1000.0 * 1.0 + 300.0 * 0.5)


def test_l10_life_matches_iso_281_closed_form():
    c_n = 20000.0
    p_n = 2000.0
    rpm = 60.0
    result = l10_life_hours(c_n, p_n, rpm, exponent=3.0)
    expected = (1.0e6 / (60.0 * rpm)) * (c_n / p_n) ** 3.0
    assert result.l10_life_hours == pytest.approx(expected, rel=1e-12)


def test_l10_life_rejects_nonpositive_inputs():
    with pytest.raises(BearingCalculationError):
        l10_life_hours(0.0, 1000.0, 60.0, exponent=3.0)
    with pytest.raises(BearingCalculationError):
        l10_life_hours(20000.0, 1000.0, -10.0, exponent=3.0)


def test_static_safety_factor_is_ratio_of_capacities():
    result = static_capacity_safety_factor(static_capacity_c0_n=15000.0, static_equivalent_load_p0_n=5000.0)
    assert result.static_safety_factor == pytest.approx(3.0)


# --- связка с VerificationRecord «не менее» --------------------------------

def test_l10_life_as_verification_record_uses_at_least_direction():
    l10 = l10_life_hours(dynamic_capacity_c_n=25000.0, equivalent_load_p_n=1800.0, rotation_speed_rpm=45.0, exponent=3.0)
    required_hours = 20000.0  # требуемый ресурс — вход из ТЗ/каталога, не выдумывается здесь
    record = VerificationRecord(
        criterion_description="l10_life", result_value=round(l10.l10_life_hours, 1), result_unit="ч",
        criterion_limit=required_hours, criterion_source="ISO 281 + требуемый ресурс (вход задания)",
        criterion_direction=CRITERION_AT_LEAST, methodology_version="bearing-1.0",
        computed_by="Инженер И.И.", reviewed_by="Инженер П.П.",
        product_revision="0.0.1", input_fingerprint="fp1",
    )
    assert l10.l10_life_hours > required_hours
    assert record.passed() is True
    ok, problems = record.is_complete_and_valid("0.0.1", "fp1")
    assert ok is True, problems


def test_l10_life_below_requirement_fails_with_at_least_direction_not_silently_flipped():
    l10 = l10_life_hours(dynamic_capacity_c_n=8000.0, equivalent_load_p_n=3000.0, rotation_speed_rpm=200.0, exponent=3.0)
    required_hours = 20000.0
    record = VerificationRecord(
        criterion_description="l10_life", result_value=round(l10.l10_life_hours, 1), result_unit="ч",
        criterion_limit=required_hours, criterion_source="ISO 281 + требуемый ресурс (вход задания)",
        criterion_direction=CRITERION_AT_LEAST, methodology_version="bearing-1.0",
        computed_by="Инженер И.И.", reviewed_by="Инженер П.П.",
        product_revision="0.0.1", input_fingerprint="fp1",
    )
    assert l10.l10_life_hours < required_hours
    assert record.passed() is False


def test_default_criterion_direction_is_at_most_unchanged_behaviour():
    """Обратная совместимость: старое поведение (напряжение <= допустимого) не изменилось по умолчанию."""
    record = VerificationRecord(
        criterion_description="bending", result_value=100.0, result_unit="МПа",
        criterion_limit=150.0, criterion_source="сопромат",
        methodology_version="1.0", computed_by="A", reviewed_by="B",
        product_revision="r1", input_fingerprint="fp",
    )
    assert record.criterion_direction == CRITERION_AT_MOST
    assert record.passed() is True
    over_limit = VerificationRecord(
        criterion_description="bending", result_value=200.0, result_unit="МПа",
        criterion_limit=150.0, criterion_source="сопромат",
        methodology_version="1.0", computed_by="A", reviewed_by="B",
        product_revision="r1", input_fingerprint="fp",
    )
    assert over_limit.passed() is False


# ---------------------------------------------------------------------------
# Codex-замечание (продолжение, 18.09.2026, п.1): exponent обязателен (нет
# умолчания), resultant_radial_load_n() отклоняет bool/строку вместо тихой
# порчи проверки через abs().
# ---------------------------------------------------------------------------

def test_l10_life_hours_requires_explicit_exponent_keyword():
    with pytest.raises(TypeError):
        l10_life_hours(20000.0, 2000.0, 60.0)  # нет exponent — не должно молча стать 3.0


def test_l10_life_hours_rejects_positional_exponent_too():
    with pytest.raises(TypeError):
        l10_life_hours(20000.0, 2000.0, 60.0, 3.0)  # exponent теперь только keyword-only


@pytest.mark.parametrize("bad", [True, False, "5", "10.0", None, [1.0], float("nan"), float("inf")])
def test_resultant_radial_load_rejects_bool_and_string_inputs(bad):
    with pytest.raises(BearingCalculationError):
        resultant_radial_load_n(bad, 4.0)
    with pytest.raises(BearingCalculationError):
        resultant_radial_load_n(4.0, bad)


def test_resultant_radial_load_accepts_signed_components():
    # Реакции в разных плоскостях могут иметь разный знак (направление) —
    # это не должно отвергаться как "отрицательная нагрузка".
    result = resultant_radial_load_n(-3.0, 4.0)
    assert result == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P1»): l10_life_hours()
# не должен возвращать inf / бросать сырой OverflowError на конечных входах,
# и exponent должен быть привязан к поддерживаемой методике ISO 281, а не к
# произвольному положительному числу.
# ---------------------------------------------------------------------------

def test_l10_life_hours_rejects_unsupported_exponent_not_matching_any_catalog_bearing_type():
    with pytest.raises(BearingCalculationError):
        l10_life_hours(20000.0, 2000.0, 60.0, exponent=2.5)


def test_l10_life_hours_accepts_roller_exponent():
    result = l10_life_hours(20000.0, 2000.0, 60.0, exponent=LIFE_EXPONENT_ROLLER)
    expected = (1.0e6 / (60.0 * 60.0)) * (20000.0 / 2000.0) ** LIFE_EXPONENT_ROLLER
    assert result.l10_life_hours == pytest.approx(expected, rel=1e-9)


def test_l10_life_hours_raises_controlled_error_instead_of_returning_inf():
    # Ранее: (C/P)**3 = (1e200/1e-200)**3 = inf, l10h тихо становился inf.
    with pytest.raises(BearingLifeOverflowError):
        l10_life_hours(1e200, 1e-200, 1.0, exponent=LIFE_EXPONENT_BALL)


def test_l10_life_hours_raises_controlled_error_instead_of_raw_overflow_error():
    # Ранее: (1e120/1)**3 бросал сырой builtins.OverflowError из оператора **.
    with pytest.raises(BearingLifeOverflowError):
        l10_life_hours(1e120, 1.0, 1.0, exponent=LIFE_EXPONENT_BALL)


def test_l10_life_hours_overflow_error_is_a_bearing_calculation_error():
    # BearingLifeOverflowError должен ловиться и общим `except BearingCalculationError`.
    with pytest.raises(BearingCalculationError):
        l10_life_hours(1e250, 1e-250, 1.0, exponent=LIFE_EXPONENT_BALL)


def test_l10_life_hours_large_but_representable_inputs_still_compute_normally():
    # Граница не должна быть слишком тесной — правдоподобно большие, но
    # физически представимые каталожные числа обязаны считаться как раньше.
    result = l10_life_hours(1e6, 1e3, 100.0, exponent=LIFE_EXPONENT_BALL)
    expected = (1.0e6 / (60.0 * 100.0)) * (1e6 / 1e3) ** LIFE_EXPONENT_BALL
    assert result.l10_life_hours == pytest.approx(expected, rel=1e-9)
    assert math.isfinite(result.l10_life_hours)


def test_l10_life_hours_huge_rpm_raises_controlled_error_not_raw_math_domain_error():
    # Независимая проверка c24d42b, раздел 3 (repro): rotation_speed_rpm=1e308
    # конечно и положительно (проходит _require_positive), но старый код
    # считал log_prefactor через math.log10(1e6/(60*rotation_speed_rpm)) —
    # `60*1e308` САМ переполнялся до `inf`, `1e6/inf=0.0`, а
    # `math.log10(0.0)` бросал СЫРОЙ `ValueError: math domain error`, а не
    # `BearingLifeOverflowError`. Префактор теперь считается как
    # `6 - log10(60) - log10(n)`, без промежуточного произведения `60*n`.
    with pytest.raises(BearingLifeOverflowError):
        l10_life_hours(1, 1, 1e308, exponent=LIFE_EXPONENT_BALL)


@pytest.mark.parametrize("rotation_speed_rpm", [1.0, 60.0, 1450.0, 1e6, 1e150, 1e307, 1e308])
def test_l10_life_hours_never_raises_raw_valueerror_for_any_finite_positive_rpm(rotation_speed_rpm):
    # Более широкая регрессия того же дефекта: для ЛЮБОГО конечного
    # положительного rotation_speed_rpm результат — либо конечное число,
    # либо контролируемый BearingLifeOverflowError, но НИКОГДА сырой
    # ValueError/OverflowError из math.log10/**.
    try:
        result = l10_life_hours(50000.0, 8000.0, rotation_speed_rpm, exponent=LIFE_EXPONENT_BALL)
    except BearingLifeOverflowError:
        return
    assert math.isfinite(result.l10_life_hours)


def test_invalid_criterion_direction_is_flagged_by_is_complete_and_valid():
    record = VerificationRecord(
        criterion_description="x", result_value=10.0, result_unit="ед",
        criterion_limit=20.0, criterion_source="src", criterion_direction="что-то_другое",
        methodology_version="1.0", computed_by="A", reviewed_by="B",
        product_revision="r1", input_fingerprint="fp",
    )
    ok, problems = record.is_complete_and_valid("r1", "fp")
    assert ok is False
    assert any("направление критерия" in p for p in problems)

# -*- coding: utf-8 -*-
"""
Реальные аналитические прочностные расчёты (раздел 3 задания).

СТАТУС: общеинженерные формулы сопротивления материалов (третья теория
прочности — теория наибольших касательных напряжений, стандартный подход
для расчёта валов на совместное действие изгиба и кручения в русскоязычных
курсах сопромата — см. источники в конце файла), НЕ являются подтверждённой
методикой Тех-Аэро и НЕ заменяют проверку инженером. Это РЕАЛЬНЫЕ расчётные
функции (не список узлов, не заглушка) — раздел 3 прямо разрешает
реализовать и проверить их на документированных контрольных примерах ДО
того, как появится конкретная CAD-модель, при условии что контрольные
примеры не выдаются за подтверждение реального изделия.

Что здесь ЕСТЬ:
- вал: напряжение от кручения (из мощности/оборотов — считается напрямую из
  результата инженерного ядра) и, если задан изгибающий момент, совместная
  проверка по эквивалентному напряжению;
- сварное соединение внахлёст/угловым швом: срез по расчётному сечению шва;
- болтовое соединение: срез по стержням болтов.

Чего здесь НЕТ и почему: изгибающий момент на валу шнека зависит от массы
спирали/трубы на погонный метр и схемы опор — этих данных нет ни в анкете,
ни в CAD (нет подключения к SolidWorks, раздел 12). Поэтому
`shaft_combined_check()` принимает изгибающий момент КАК ВХОДНОЙ ПАРАМЕТР,
который инженер должен посчитать или получить из CAD — функция не подставляет
за него выдуманное значение (раздел 3: "не назначай всем элементам один
произвольный коэффициент запаса").
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# Справочные допускаемые напряжения (раздел 3 — общеинженерные величины,
# НЕ являются нормативным актом; статус "справочно", применимость к
# конкретной стали/сварке/классу прочности болта инженер обязан проверить).
STEEL_YIELD_MPA = {
    "Ст3": 235.0,
    "40Х": 785.0,
    "45": 360.0,
}

# Допускаемое напряжение среза для углового шва стали Ст3, общеинженерный
# ориентир (≈0.55-0.6 от предела текучести металла шва при ручной дуговой
# сварке электродами Э42/Э46) — ТРЕБУЕТ подтверждения по применимому ГОСТ.
DEFAULT_WELD_ALLOWABLE_SHEAR_MPA = 100.0

# Допускаемое напряжение среза для болтов класса прочности 8.8, общеинженерный
# ориентир (при коэффициенте запаса ~2.5 от предела текучести ~640 МПа) —
# ТРЕБУЕТ подтверждения по применимому ГОСТ/расчёту.
DEFAULT_BOLT_ALLOWABLE_SHEAR_MPA = 190.0


class StrengthCalculationError(ValueError):
    pass


@dataclass
class StrengthCheckOutcome:
    """Прямо конвертируется в VerificationRecord — то же самое число, тот же критерий."""

    criterion_description: str
    result_value: float
    result_unit: str
    criterion_limit: float
    criterion_source: str
    method: str
    safety_factor: Optional[float] = None
    inputs_used: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.result_value <= self.criterion_limit


def _require_positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise StrengthCalculationError(f"{name}: ожидалось конечное число, получено {value!r}.")
    if value <= 0:
        raise StrengthCalculationError(f"{name}: должно быть больше нуля, получено {value}.")


def torque_from_power(shaft_power_kw: float, rotation_speed_rpm: float) -> float:
    """
    Крутящий момент на валу, Н·м, из мощности (кВт) и частоты вращения
    (об/мин) — стандартная формула T[Н*м] = 9550 * P[кВт] / n[об/мин].
    """
    _require_positive("shaft_power_kw", shaft_power_kw)
    _require_positive("rotation_speed_rpm", rotation_speed_rpm)
    return 9550.0 * shaft_power_kw / rotation_speed_rpm


def shaft_torsion_only_check(
    shaft_diameter_mm: float,
    torque_nm: float,
    material: str = "Ст3",
    safety_factor: float = 3.0,
) -> StrengthCheckOutcome:
    """
    Напряжение кручения в сплошном круглом валу: τ = T / Wp, Wp = π*d³/16.
    Единственная нагрузка, которую можно посчитать БЕЗ данных CAD (крутящий
    момент известен из мощности/оборотов инженерного ядра; изгибающий момент
    — нет, см. docstring модуля). Допускаемое напряжение = предел текучести /
    коэффициент запаса (безопасности) — консервативная оценка (полное
    касательное напряжение при кручении сравнивается с нормальным пределом
    текучести — это на стороне запаса, а не самая точная модель).
    """
    _require_positive("shaft_diameter_mm", shaft_diameter_mm)
    _require_positive("torque_nm", torque_nm)
    if material not in STEEL_YIELD_MPA:
        raise StrengthCalculationError(
            f"Материал {material!r} отсутствует в справочнике STEEL_YIELD_MPA — добавьте "
            "подтверждённое значение предела текучести перед расчётом."
        )
    d_m = shaft_diameter_mm / 1000.0
    wp_m3 = math.pi * d_m ** 3 / 16.0
    tau_pa = torque_nm / wp_m3
    tau_mpa = tau_pa / 1e6

    yield_mpa = STEEL_YIELD_MPA[material]
    allowable_mpa = yield_mpa / safety_factor

    return StrengthCheckOutcome(
        criterion_description=f"вал: напряжение кручения (Ø{shaft_diameter_mm:.0f} мм, {material})",
        result_value=round(tau_mpa, 2),
        result_unit="МПа",
        criterion_limit=round(allowable_mpa, 2),
        criterion_source=f"σ_т({material})={yield_mpa} МПа / n={safety_factor} (общеинженерный запас, сопромат)",
        method="аналитический_расчёт",
        safety_factor=safety_factor,
        inputs_used={"shaft_diameter_mm": shaft_diameter_mm, "torque_nm": torque_nm, "material": material},
    )


def shaft_combined_check(
    shaft_diameter_mm: float,
    torque_nm: float,
    bending_moment_nm: float,
    material: str = "Ст3",
    safety_factor: float = 2.0,
) -> StrengthCheckOutcome:
    """
    Совместное действие изгиба и кручения по третьей теории прочности
    (теория наибольших касательных напряжений):

        σ_экв = sqrt(σ_изг² + 4·τ_кр²)

    где σ_изг = M_изг / W, τ_кр = T / Wp, W = π*d³/32, Wp = π*d³/16 для
    сплошного круглого сечения. bending_moment_nm — ОБЯЗАТЕЛЬНЫЙ входной
    параметр: эта функция не подставляет его сама (раздел 3 — не назначай
    нагрузку произвольно; изгибающий момент нужно получить из схемы нагрузок
    конкретного вала, которой пока нет без CAD/паспорта опор).
    """
    _require_positive("shaft_diameter_mm", shaft_diameter_mm)
    _require_positive("torque_nm", torque_nm)
    if not isinstance(bending_moment_nm, (int, float)) or isinstance(bending_moment_nm, bool) \
            or not math.isfinite(bending_moment_nm) or bending_moment_nm < 0:
        raise StrengthCalculationError(
            f"bending_moment_nm: ожидалось неотрицательное конечное число, получено {bending_moment_nm!r}."
        )
    if material not in STEEL_YIELD_MPA:
        raise StrengthCalculationError(f"Материал {material!r} отсутствует в справочнике STEEL_YIELD_MPA.")

    d_m = shaft_diameter_mm / 1000.0
    w_m3 = math.pi * d_m ** 3 / 32.0
    wp_m3 = math.pi * d_m ** 3 / 16.0

    sigma_bend_mpa = (bending_moment_nm / w_m3) / 1e6
    tau_torsion_mpa = (torque_nm / wp_m3) / 1e6
    sigma_eq_mpa = math.sqrt(sigma_bend_mpa ** 2 + 4.0 * tau_torsion_mpa ** 2)

    yield_mpa = STEEL_YIELD_MPA[material]
    allowable_mpa = yield_mpa / safety_factor

    return StrengthCheckOutcome(
        criterion_description=f"вал: эквивалентное напряжение изгиб+кручение (Ø{shaft_diameter_mm:.0f} мм, {material})",
        result_value=round(sigma_eq_mpa, 2),
        result_unit="МПа",
        criterion_limit=round(allowable_mpa, 2),
        criterion_source=(
            f"3-я теория прочности: σ_экв=sqrt(σ²+4τ²); σ_т({material})={yield_mpa} МПа / n={safety_factor}"
        ),
        method="аналитический_расчёт",
        safety_factor=safety_factor,
        inputs_used={
            "shaft_diameter_mm": shaft_diameter_mm, "torque_nm": torque_nm,
            "bending_moment_nm": bending_moment_nm, "material": material,
        },
    )


def weld_shear_check(
    load_n: float,
    weld_leg_mm: float,
    weld_length_mm: float,
    allowable_shear_mpa: float = DEFAULT_WELD_ALLOWABLE_SHEAR_MPA,
) -> StrengthCheckOutcome:
    """
    Срез углового шва по расчётному сечению: τ = F / (0.7 * k * L), где
    k — катет шва, L — расчётная длина шва, 0.7*k — толщина расчётного
    сечения углового шва (стандартное допущение для сварных швов).
    """
    _require_positive("load_n", load_n)
    _require_positive("weld_leg_mm", weld_leg_mm)
    _require_positive("weld_length_mm", weld_length_mm)
    _require_positive("allowable_shear_mpa", allowable_shear_mpa)

    throat_mm = 0.7 * weld_leg_mm
    area_mm2 = throat_mm * weld_length_mm
    tau_mpa = load_n / area_mm2

    return StrengthCheckOutcome(
        criterion_description=f"сварной шов: срез (катет {weld_leg_mm:.0f} мм, длина {weld_length_mm:.0f} мм)",
        result_value=round(tau_mpa, 2),
        result_unit="МПа",
        criterion_limit=round(allowable_shear_mpa, 2),
        criterion_source=f"[a] допускаемое напряжение среза шва, справочно = {allowable_shear_mpa} МПа — "
                          "требует подтверждения по применимому ГОСТ/СП для конкретного электрода и стали",
        method="аналитический_расчёт",
        inputs_used={"load_n": load_n, "weld_leg_mm": weld_leg_mm, "weld_length_mm": weld_length_mm},
    )


def bolt_group_shear_check(
    load_n: float,
    bolt_count: int,
    bolt_diameter_mm: float,
    allowable_shear_mpa: float = DEFAULT_BOLT_ALLOWABLE_SHEAR_MPA,
) -> StrengthCheckOutcome:
    """Срез группы болтов равными долями: τ = F / (n_болтов * A_болта)."""
    _require_positive("load_n", load_n)
    _require_positive("bolt_diameter_mm", bolt_diameter_mm)
    _require_positive("allowable_shear_mpa", allowable_shear_mpa)
    if not isinstance(bolt_count, int) or bolt_count <= 0:
        raise StrengthCalculationError(f"bolt_count: ожидалось положительное целое, получено {bolt_count!r}.")

    area_mm2 = math.pi * (bolt_diameter_mm ** 2) / 4.0
    tau_mpa = load_n / (bolt_count * area_mm2)

    return StrengthCheckOutcome(
        criterion_description=f"болтовое соединение: срез ({bolt_count} x M{bolt_diameter_mm:.0f})",
        result_value=round(tau_mpa, 2),
        result_unit="МПа",
        criterion_limit=round(allowable_shear_mpa, 2),
        criterion_source=f"[a] допускаемое напряжение среза болта, справочно = {allowable_shear_mpa} МПа — "
                          "требует подтверждения по классу прочности и применимому расчёту",
        method="аналитический_расчёт",
        inputs_used={"load_n": load_n, "bolt_count": bolt_count, "bolt_diameter_mm": bolt_diameter_mm},
    )


# ---------------------------------------------------------------------------
# Источники (общеинженерные формулы сопротивления материалов, публикуются в
# стандартных курсах и справочниках):
# - третья теория прочности для валов: Писаренко Г.С. и др., "Сопротивление
#   материалов"; Александров А.В., "Сопротивление материалов".
# - расчёт углового сварного шва на срез: тот же класс справочников,
#   раздел "Расчёт сварных соединений".
# - расчёт болтовых соединений на срез: тот же класс справочников, раздел
#   "Расчёт болтовых/заклёпочных соединений".
# Значения допускаемых напряжений отмечены "[a]" — общеинженерные ориентиры,
# НЕ нормативные величины Тех-Аэро; статус проверки: НЕ ПРОВЕРЕНО.
# ---------------------------------------------------------------------------

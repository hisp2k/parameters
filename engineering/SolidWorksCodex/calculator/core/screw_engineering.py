# -*- coding: utf-8 -*-
"""
Инженерное ядро для валового желобчатого шнекового транспортёра.

СТАТУС: ЧЕРНОВИК, НЕ ПРОВЕРЕНО инженером Тех-Аэро (см. вопрос №3 в
QUESTIONS_FOR_DMITRY_ALEXANDROVICH_RU.md в ветке claude/director-parametric-pilot).
Формулы и коэффициенты — общеинженерные, встречающиеся в открытых отраслевых
методичках расчёта винтовых/шнековых конвейеров (см. список источников в
конце файла), НЕ являются подтверждённой методикой Тех-Аэро. Использовать
результат этого модуля только как ПРЕДВАРИТЕЛЬНУЮ оценку (см.
ParamStatus.CALCULATED_PRELIMINARY) — никогда не как основание для
производственного выпуска (это явно проверяется release_gate.py).

История исправлений (нумерация сохранена из предыдущей версии файла, новые
пункты добавлены по итогам инженерной проверки задания от 16.09.2026):

1. Нулевая/отрицательная плотность и нулевая/отрицательная производительность
   отклоняются здесь (ValueError), а не только в интерфейсе.
2. `forced_step_mm`, заданный БЕЗ `forced_diameter_mm`, теперь используется на
   каждой рассматриваемой стандартной ступени диаметра (раньше игнорировался).
3. Когда расчётная мощность превышает верхнюю границу стандартного ряда
   моторов, `motor_power_kw` = None и `motor_selection_ok = False`, а не
   самый мощный мотор ряда молча выданный за подобранный.
4. (раздел 1.В задания) РАЗДЕЛЕНЫ требуемая и достижимая производительность.
   Раньше при ограничении оборотов (n_required > n_max) частота вращения
   обрезалась до n_max, но в результате производительность всё равно
   выводилась равной ТРЕБУЕМОЙ (q_t_h) — то есть неподходящий по оборотам
   вариант показывался как будто он выполняет задание. Теперь:
   - `productivity_required_t_per_h` — то, что просили;
   - `productivity_achievable_t_per_h` — то, что реально получится на
     ФАКТИЧЕСКИ используемой (после ограничения) частоте вращения;
   - `requirement_met` — явный флаг "выполнено ли задание", а не то, что
     нужно домысливать по разнице чисел.
5. (раздел 1.Д) Входные числа проверяются на NaN/Infinity и на тип — раньше
   `bulk_density_kg_m3 <= 0` для `float('nan')` возвращает `False` в Python
   (сравнение с NaN всегда ложно), поэтому NaN проходил проверку "больше
   нуля" и приводил к NaN на выходе без единого явного предупреждения.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --- Справочные ряды и коэффициенты (см. источники в конце файла) --------

STANDARD_DIAMETERS_MM = [100, 125, 160, 200, 250, 320, 400, 500, 650, 800]

STANDARD_MOTOR_KW = [0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11.0, 15.0, 18.5, 22.0]


class Abrasiveness:
    LOW = "низкая"
    MEDIUM = "средняя"
    HIGH = "высокая"


FILL_FACTOR_PSI = {Abrasiveness.LOW: 0.40, Abrasiveness.MEDIUM: 0.30, Abrasiveness.HIGH: 0.25}
STEP_TO_DIAMETER_RATIO = {Abrasiveness.LOW: 1.0, Abrasiveness.MEDIUM: 0.9, Abrasiveness.HIGH: 0.8}
RESISTANCE_OMEGA = {Abrasiveness.LOW: 1.2, Abrasiveness.MEDIUM: 2.5, Abrasiveness.HIGH: 4.0}
MAX_SPEED_A = {Abrasiveness.LOW: 65.0, Abrasiveness.MEDIUM: 45.0, Abrasiveness.HIGH: 30.0}

LUMP_FACTOR_ORDINARY = 4.0
LUMP_FACTOR_SORTED = 12.0

DRIVE_EFFICIENCY = 0.88
POWER_SAFETY_MARGIN = 1.25


class EngineeringInputError(ValueError):
    """Некорректные входные данные для инженерного ядра (не путать с warnings)."""


def _require_finite_number(name: str, value, allow_none: bool = False) -> None:
    """
    Раздел 1.Д: "Отклоняй NaN, Infinity, неверные типы и недопустимые
    значения". `value <= 0` в Python молча пропускает NaN (сравнение с NaN
    всегда False) — поэтому недостаточно полагаться на обычные сравнения,
    нужна отдельная явная проверка типа и конечности числа.
    """
    if value is None:
        if allow_none:
            return
        raise EngineeringInputError(f"{name}: значение отсутствует (None).")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EngineeringInputError(f"{name}: ожидалось число, получено {type(value).__name__} ({value!r}).")
    if not math.isfinite(value):
        raise EngineeringInputError(f"{name}: значение должно быть конечным числом, получено {value!r}.")


def incline_correction_c(angle_deg: float) -> float:
    if angle_deg <= 0:
        return 1.0
    if angle_deg <= 10:
        return 0.9
    if angle_deg <= 20:
        return 0.75
    raise EngineeringInputError(
        "Угол наклона > 20° требует отдельной методики расчёта "
        "(круто наклонные/вертикальные шнеки) — не покрыто этим черновиком."
    )


@dataclass
class ScrewEngineeringInput:
    productivity_value: float
    productivity_unit: str  # "т/ч" | "кг/ч" | "м3/ч"
    bulk_density_kg_m3: float
    max_lump_size_mm: float
    is_sorted_material: bool
    abrasiveness: str
    working_length_mm: float
    incline_deg: float
    forced_diameter_mm: float | None = None
    forced_step_mm: float | None = None


@dataclass
class ScrewEngineeringResult:
    diameter_mm: float
    step_mm: float

    # Раздел 1.В — разделены требуемая частота, допустимая по абразивности и
    # диаметру, и фактически применённая (после ограничения).
    rotation_speed_rpm: float                 # фактически используемая (после ограничения)
    required_rotation_speed_rpm: float        # какая нужна была бы для 100% требуемой производительности
    max_allowed_rotation_speed_rpm: float     # допустимая по А/√D (ограничение по материалу)

    shaft_power_kw: float
    motor_power_kw: float | None
    motor_selection_ok: bool
    fill_factor_psi: float
    incline_factor_c: float

    # Раздел 1.В — требуемая и ДОСТИЖИМАЯ производительность разделены.
    productivity_required_t_per_h: float
    productivity_achievable_t_per_h: float
    requirement_met: bool

    warnings: list[str] = field(default_factory=list)

    @property
    def productivity_t_per_h(self) -> float:
        """
        Обратная совместимость со старым именем поля: раньше был один смысл
        "производительность", который на самом деле был ТРЕБУЕМЫМ значением.
        Оставлено как алиас, чтобы старый код не читал молча неверное число,
        но новый код должен использовать явные *_required_/*_achievable_.
        """
        return self.productivity_required_t_per_h


def _productivity_to_t_per_h(value: float, unit: str, density_kg_m3: float) -> float:
    unit_n = unit.strip().lower()
    if unit_n in ("т/ч", "t/h"):
        return value
    if unit_n in ("кг/ч", "kg/h"):
        return value / 1000.0
    if unit_n in ("м3/ч", "м³/ч", "m3/h"):
        return value * density_kg_m3 / 1000.0
    raise EngineeringInputError(f"Неизвестная единица производительности: {unit!r}")


def compute_engineering_core(inp: ScrewEngineeringInput) -> ScrewEngineeringResult:
    _require_finite_number("bulk_density_kg_m3", inp.bulk_density_kg_m3)
    _require_finite_number("productivity_value", inp.productivity_value)
    _require_finite_number("max_lump_size_mm", inp.max_lump_size_mm)
    _require_finite_number("working_length_mm", inp.working_length_mm)
    _require_finite_number("incline_deg", inp.incline_deg)
    _require_finite_number("forced_diameter_mm", inp.forced_diameter_mm, allow_none=True)
    _require_finite_number("forced_step_mm", inp.forced_step_mm, allow_none=True)

    if inp.bulk_density_kg_m3 <= 0:
        raise EngineeringInputError(
            f"Насыпная плотность должна быть больше нуля, получено {inp.bulk_density_kg_m3}."
        )
    if inp.productivity_value <= 0:
        raise EngineeringInputError(
            f"Производительность должна быть больше нуля, получено {inp.productivity_value}."
        )
    if inp.working_length_mm <= 0:
        raise EngineeringInputError(
            f"Рабочая длина должна быть больше нуля, получено {inp.working_length_mm}."
        )
    if inp.forced_diameter_mm is not None and inp.forced_diameter_mm <= 0:
        raise EngineeringInputError(
            f"Заданный диаметр должен быть больше нуля, получено {inp.forced_diameter_mm}."
        )
    if inp.forced_step_mm is not None and inp.forced_step_mm <= 0:
        raise EngineeringInputError(
            f"Заданный шаг должен быть больше нуля, получено {inp.forced_step_mm}."
        )
    if inp.abrasiveness not in FILL_FACTOR_PSI:
        raise EngineeringInputError(f"Неизвестная абразивность: {inp.abrasiveness!r}")
    if not isinstance(inp.is_sorted_material, bool):
        raise EngineeringInputError(
            f"is_sorted_material должен быть булевым значением, получено {inp.is_sorted_material!r}."
        )

    warnings: list[str] = []

    q_t_h_required = _productivity_to_t_per_h(inp.productivity_value, inp.productivity_unit, inp.bulk_density_kg_m3)
    density_t_m3 = inp.bulk_density_kg_m3 / 1000.0
    psi = FILL_FACTOR_PSI[inp.abrasiveness]
    e_ratio = STEP_TO_DIAMETER_RATIO[inp.abrasiveness]
    c = incline_correction_c(inp.incline_deg)
    a_max = MAX_SPEED_A[inp.abrasiveness]

    lump_factor = LUMP_FACTOR_SORTED if inp.is_sorted_material else LUMP_FACTOR_ORDINARY
    min_diameter_mm = inp.max_lump_size_mm * lump_factor
    q_m3_h_required = q_t_h_required / density_t_m3

    def cross_section_flow_per_rpm(diameter_mm: float, step_mm: float) -> float:
        """м3/ч, которые проходят через сечение за 1 об/мин (не путать с расходом)."""
        d_m = diameter_mm / 1000.0
        s_m = step_mm / 1000.0
        value = 60.0 * (math.pi * d_m ** 2 / 4.0) * s_m * psi * c
        if value <= 0:
            raise EngineeringInputError("Некорректные входные данные: нулевое сечение потока.")
        return value

    def n_required_and_max(diameter_mm: float, step_mm: float) -> tuple[float, float]:
        flow_per_rpm = cross_section_flow_per_rpm(diameter_mm, step_mm)
        d_m = diameter_mm / 1000.0
        n_req = q_m3_h_required / flow_per_rpm
        n_max_ = a_max / math.sqrt(d_m)
        return n_req, n_max_

    def step_for(diameter_mm: float) -> float:
        # Исправление №2: явно заданный шаг используется независимо от того,
        # задан ли диаметр вручную или подбирается автоматически.
        return inp.forced_step_mm if inp.forced_step_mm is not None else diameter_mm * e_ratio

    if inp.forced_diameter_mm is not None:
        diameter_mm = inp.forced_diameter_mm
        step_mm = step_for(diameter_mm)
        if diameter_mm < min_diameter_mm:
            warnings.append(
                f"Заданный диаметр {diameter_mm} мм меньше минимально допустимого по крупности "
                f"куска ({min_diameter_mm:.0f} мм) — требуется проверка инженером."
            )
        n_required, n_max = n_required_and_max(diameter_mm, step_mm)
        if n_required > n_max:
            warnings.append(
                f"При заданном диаметре {diameter_mm} мм требуемая частота вращения "
                f"({n_required:.2f} об/мин) превышает максимально допустимую ({n_max:.2f} об/мин) — "
                "заданная производительность НЕ будет достигнута на этом диаметре."
            )
        n_rpm_used = min(n_required, n_max)
    else:
        diameter_mm = None
        step_mm = None
        n_required = None
        n_max = None
        n_rpm_used = None
        for candidate_d in STANDARD_DIAMETERS_MM:
            if candidate_d < min_diameter_mm:
                continue
            candidate_step = step_for(candidate_d)
            candidate_n_required, candidate_n_max = n_required_and_max(candidate_d, candidate_step)
            if candidate_n_required <= candidate_n_max:
                diameter_mm, step_mm = candidate_d, candidate_step
                n_required, n_max = candidate_n_required, candidate_n_max
                n_rpm_used = n_required
                break
        if diameter_mm is None:
            diameter_mm = STANDARD_DIAMETERS_MM[-1]
            step_mm = step_for(diameter_mm)
            n_required, n_max = n_required_and_max(diameter_mm, step_mm)
            n_rpm_used = min(n_required, n_max)
            reason = (
                f"превышает максимум стандартного ряда ({diameter_mm} мм)"
                if min_diameter_mm > diameter_mm
                else "не позволяет обеспечить заданную производительность при безопасной "
                     "частоте вращения ни на одном стандартном диаметре"
            )
            warnings.append(
                f"Требуемый диаметр по крупности куска ({min_diameter_mm:.0f} мм) {reason} — "
                "нужен нестандартный шнек или пересмотр требований, решение за инженером."
            )

    # Раздел 1.В: пересчитываем ДОСТИЖИМУЮ производительность от фактически
    # применённой (после ограничения) частоты вращения — а не выводим
    # запрошенное значение как будто оно гарантировано.
    flow_per_rpm_final = cross_section_flow_per_rpm(diameter_mm, step_mm)
    q_m3_h_achievable = flow_per_rpm_final * n_rpm_used
    q_t_h_achievable = q_m3_h_achievable * density_t_m3

    requirement_met = q_t_h_achievable >= q_t_h_required * 0.999  # допуск на округление
    if not requirement_met:
        shortfall_pct = (1.0 - q_t_h_achievable / q_t_h_required) * 100.0
        warnings.append(
            f"Требуемая производительность НЕ выполняется: достижимо "
            f"{q_t_h_achievable:.2f} т/ч из требуемых {q_t_h_required:.2f} т/ч "
            f"(дефицит {shortfall_pct:.0f}%) при ограничении оборотов до "
            f"{n_max:.2f} об/мин по допустимой скорости для данной абразивности/диаметра."
        )

    working_length_m = inp.working_length_mm / 1000.0
    height_gain_m = working_length_m * math.sin(math.radians(inp.incline_deg))
    omega = RESISTANCE_OMEGA[inp.abrasiveness]

    # Мощность считаем от ДОСТИЖИМОЙ производительности (реальная нагрузка на
    # привод соответствует тому, что фактически будет перемещаться), а не от
    # требуемой, если они разошлись из-за ограничения оборотов.
    shaft_power_kw = (q_t_h_achievable * working_length_m * omega + q_t_h_achievable * height_gain_m) / 367.0
    motor_power_kw_raw = shaft_power_kw / DRIVE_EFFICIENCY * POWER_SAFETY_MARGIN

    motor_power_kw = next((p for p in STANDARD_MOTOR_KW if p >= motor_power_kw_raw), None)
    motor_selection_ok = motor_power_kw is not None
    if not motor_selection_ok:
        # Исправление №3: не возвращаем самый мощный мотор ряда как будто он
        # подошёл — явно сообщаем, что подбор не дал результата.
        warnings.append(
            f"Расчётная мощность ({motor_power_kw_raw:.2f} кВт) превышает верхнюю границу "
            f"стандартного ряда этого черновика ({STANDARD_MOTOR_KW[-1]} кВт) — подходящий "
            "мотор не подобран, нужен каталог приводов поставщика с большей мощностью."
        )

    return ScrewEngineeringResult(
        diameter_mm=diameter_mm,
        step_mm=step_mm,
        rotation_speed_rpm=round(n_rpm_used, 2),
        required_rotation_speed_rpm=round(n_required, 2),
        max_allowed_rotation_speed_rpm=round(n_max, 2),
        shaft_power_kw=round(shaft_power_kw, 3),
        motor_power_kw=motor_power_kw,
        motor_selection_ok=motor_selection_ok,
        fill_factor_psi=psi,
        incline_factor_c=c,
        productivity_required_t_per_h=round(q_t_h_required, 3),
        productivity_achievable_t_per_h=round(q_t_h_achievable, 3),
        requirement_met=requirement_met,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Источники (формулы — общеинженерные, публикуются во множестве методичек;
# то же, что использовано в исходном черновике Stage 12):
# - https://bigspiral.ru/raschet-shnekovogo-transportera-proizvoditelnost-diametr-moshhnost/
# - https://studfile.net/preview/17025552/page:3/
# Статус проверки: НЕ ПРОВЕРЕНО Тех-Аэро (см. вопрос №3 в своде вопросов).
# ---------------------------------------------------------------------------

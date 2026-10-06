# -*- coding: utf-8 -*-
"""
Совместный расчёт относительного зазора вал/корпус (независимая проверка
коммита 377e33c, продолжение 18.09.2026, раздел «P0. Посчитать
относительный зазор»).

ЧТО БЫЛО НЕ ТАК. `tests/test_housing_frame_synthetic_example.py` считал
расход зазора как

    shaft_deflection_demo_mm = 0.35            # ПРОИЗВОЛЬНО подставленное число
    housing_deflection_mm = |прогиб корпуса в H_LOAD_A|
    consumed = shaft_deflection_demo_mm + housing_deflection_mm

Это НЕ проверка совместного перемещения: `0.35` не было результатом
НИКАКОГО расчёта вала (ни этого, ни какого-либо другого), и даже если бы
оба числа были реальными прогибами, их модули складывались автоматически
— то есть перемещения вала и корпуса В ОДНУ СТОРОНУ (частично гасящие друг
друга) и В РАЗНЫЕ СТОРОНЫ (складывающиеся) были бы неотличимы. Задание
прямо требует: "Расход радиального зазора определяй по поперечной
составляющей разности векторов перемещения осей... Не складывай модули
перемещений автоматически."

ПРАВИЛЬНАЯ ПОСТАНОВКА.
1. Оба перемещения — оси вала и оси корпуса (расточки под подшипник) —
   берутся В ОДНОМ сечении (одна и та же осевая координата x), в ОДНОЙ
   системе координат (см. core/load_transfer.py — правая XYZ, мм) и для
   ОДНОГО режима нагружения (не "рабочий режим вала" + независимо взятое
   число для корпуса).
2. Прогиб вала из `core/shaft_beam_model.py::BeamSolution.deflection_mm()`
   посчитан ОТНОСИТЕЛЬНО его собственных опор (условие y=0 на обеих
   опорах, см. docstring `solve_deflection`) — это НЕ абсолютное положение
   оси вала в пространстве, если сами опоры (подшипниковые узлы корпуса)
   тоже смещаются под нагрузкой. АБСОЛЮТНОЕ поперечное перемещение оси
   вала = его относительный прогиб + перемещение самих опор в этой же
   точке, линейно интерполированное между двумя опорами по осевой
   координате (`shaft_absolute_lateral_displacement_mm`).
3. Расход зазора в сечении — модуль ВЕКТОРНОЙ разности (перемещение оси
   вала минус перемещение оси корпуса) В ПЛОСКОСТИ сечения (2 ортогональные
   поперечные компоненты, здесь условно Y/Z — см. `LateralDisplacement`),
   а НЕ сумма модулей каждого перемещения по отдельности:
   - одинаковые перемещения (обе оси сместились в одну сторону на одну
     величину) → разность = 0 → зазор НЕ расходуется;
   - противоположные перемещения → разность = сумма модулей → зазор
     расходуется МАКСИМАЛЬНО;
   - ортогональные перемещения (в двух разных направлениях поперечной
     плоскости) → разность считается по теореме Пифагора (векторно), а
     не арифметическим сложением модулей.
4. Критическое сечение — то из заданного набора кандидатов ВДОЛЬ ДЛИНЫ
   (`critical_section_clearance`), где расход зазора (до добавления
   биения/допусков — они не зависят от выбора сечения) максимален.

ЧЕСТНОЕ ОГРАНИЧЕНИЕ ЭТОЙ ВЕРСИИ (см. также FrameModel.known_limitations):
абсолютное перемещение корпуса берётся ТОЛЬКО в узлах, явно присутствующих
в модели корпуса (`FrameSolution.displacement_at`) — между узлами
перемещение НЕ интерполируется по форме балки (кубическая функция формы),
только по узлам. Для схем, где точки приложения нагрузки/опоры вала уже
являются узлами корпуса (как в синтетическом примере), это не приближение
«между точками», а точное значение В ЭТИХ точках; для сечений СТРОГО между
узлами данная версия не оценивает промежуточное значение — это открытая
методологическая проверка, а не скрытая, см. `critical_section_clearance`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

from calculator.core.shaft_beam_model import ClearanceCheck, ShaftBeamModelError, clearance_check


class ShaftHousingClearanceError(ValueError):
    pass


def _finite(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShaftHousingClearanceError(f"{name}: ожидалось число, получено {type(value).__name__} ({value!r}).")
    if not math.isfinite(value):
        raise ShaftHousingClearanceError(f"{name}: значение должно быть конечным числом, получено {value!r}.")
    return float(value)


@dataclass(frozen=True)
class LateralDisplacement:
    """
    Поперечное перемещение оси в сечении — 2 компоненты в плоскости,
    перпендикулярной оси вала (условно Y/Z глобальной системы координат
    core/load_transfer.py). Не путать с продольным (осевым) перемещением —
    оно на расход РАДИАЛЬНОГО зазора не влияет.
    """

    dy_mm: float
    dz_mm: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "dy_mm", _finite("dy_mm", self.dy_mm))
        object.__setattr__(self, "dz_mm", _finite("dz_mm", self.dz_mm))

    def __sub__(self, other: "LateralDisplacement") -> "LateralDisplacement":
        return LateralDisplacement(self.dy_mm - other.dy_mm, self.dz_mm - other.dz_mm)

    def magnitude_mm(self) -> float:
        return math.hypot(self.dy_mm, self.dz_mm)


def clearance_consumption_from_vectors(
    shaft_displacement: LateralDisplacement, housing_displacement: LateralDisplacement,
) -> float:
    """
    Расход зазора по ВЕКТОРНОЙ разности перемещений (см. докстринг модуля,
    п.3) — единственное место, где определяется "сколько зазора съедено
    прогибом" в ОДНОМ сечении. Специально НЕ `abs(shaft)+abs(housing)`.
    """
    return (shaft_displacement - housing_displacement).magnitude_mm()


def interpolate_between_supports(
    x_mm: float, x0_mm: float, v0: float, x1_mm: float, v1: float, *, what: str = "величина",
) -> float:
    """
    Линейная интерполяция МЕЖДУ двумя известными точками (x0,v0)-(x1,v1).
    Экстраполяция ЗА пределы отрезка запрещена явно (нет данных о
    поведении вне модели опор — не додумываем).
    """
    x_mm = _finite("x_mm", x_mm)
    x0_mm = _finite("x0_mm", x0_mm)
    x1_mm = _finite("x1_mm", x1_mm)
    v0 = _finite(f"{what}[0]", v0)
    v1 = _finite(f"{what}[1]", v1)
    if abs(x1_mm - x0_mm) < 1e-9:
        raise ShaftHousingClearanceError(f"x0_mm и x1_mm совпадают ({x0_mm}) — интерполяция не определена.")
    lo, hi = (x0_mm, x1_mm) if x0_mm <= x1_mm else (x1_mm, x0_mm)
    if not (lo - 1e-6 <= x_mm <= hi + 1e-6):
        raise ShaftHousingClearanceError(
            f"x_mm={x_mm} вне диапазона опор [{lo}, {hi}] — экстраполяция за пределы "
            "модели запрещена (нет проверенных данных о перемещении вне опор)."
        )
    t = (x_mm - x0_mm) / (x1_mm - x0_mm)
    return v0 + t * (v1 - v0)


def shaft_absolute_lateral_displacement_mm(
    x_mm: float,
    support_a_position_mm: float, support_a_absolute: LateralDisplacement,
    support_b_position_mm: float, support_b_absolute: LateralDisplacement,
    relative_dy_mm: float = 0.0, relative_dz_mm: float = 0.0,
) -> LateralDisplacement:
    """
    АБСОЛЮТНОЕ поперечное перемещение оси вала в сечении x_mm (см.
    докстринг модуля, п.2) = относительный прогиб вала В ЭТОЙ точке
    (`relative_dy_mm`/`relative_dz_mm` — берётся из BeamSolution.
    deflection_mm() для соответствующей плоскости изгиба, 0.0 если эта
    плоскость не нагружена/не считалась) + перемещение самих опор,
    линейно интерполированное между `support_a`/`support_b` (перемещение
    опор — из решения КОРПУСА в тех же узлах, где стоят подшипники, см.
    `FrameSolution.displacement_at`).
    """
    abs_dy = relative_dy_mm + interpolate_between_supports(
        x_mm, support_a_position_mm, support_a_absolute.dy_mm,
        support_b_position_mm, support_b_absolute.dy_mm, what="опора_dy",
    )
    abs_dz = relative_dz_mm + interpolate_between_supports(
        x_mm, support_a_position_mm, support_a_absolute.dz_mm,
        support_b_position_mm, support_b_absolute.dz_mm, what="опора_dz",
    )
    return LateralDisplacement(abs_dy, abs_dz)


def rigid_offset_lateral_displacement(
    node_uy_mm: float, node_uz_mm: float, twist_rx_rad: float,
    offset_y_mm: float, offset_z_mm: float,
) -> LateralDisplacement:
    """
    Абсолютное поперечное перемещение ТОЧКИ, смещённой от узла модели на
    (offset_y_mm, offset_z_mm) в плоскости поперечного сечения, при
    известном перемещении самого узла (node_uy_mm, node_uz_mm) и его
    повороте вокруг ПРОДОЛЬНОЙ оси балки (twist_rx_rad, малый угол, рад).

    Независимая проверка коммита c24d42b, раздел 1 ("если точки крепления
    смещены относительно осей, передавай не только силы и моменты, но и
    кинематику жёсткого смещения: u_точки = u_узла + θ × r. Не имитируй
    жёсткую связь произвольно огромной жёсткостью") — это ЧИСТОЕ
    post-processing преобразование уже полученного решения `FrameModel`,
    БЕЗ добавления в модель фиктивного сверхжёсткого элемента:

        θ = (rx, 0, 0)         — поворот узла вокруг локальной оси балки
        r = (0, offset_y, offset_z)  — вектор ОТ узла К смещённой точке
        θ × r = (0·offset_z − 0·offset_y,
                  0·0 − rx·offset_z,
                  rx·offset_y − 0·0) = (0, −rx·offset_z, rx·offset_y)

    т.е. u_точки = u_узла + θ×r даёт:
        dy_точки = node_uy_mm − twist_rx_rad · offset_z_mm
        dz_точки = node_uz_mm + twist_rx_rad · offset_y_mm

    При offset=(0,0) сводится к перемещению самого узла (см. тесты).
    Малые повороты (линейная кинематика) — то же допущение, что и во всём
    остальном балочном расчёте этого репозитория (Эйлер–Бернулли,
    линейная теория упругости).
    """
    node_uy_mm = _finite("node_uy_mm", node_uy_mm)
    node_uz_mm = _finite("node_uz_mm", node_uz_mm)
    twist_rx_rad = _finite("twist_rx_rad", twist_rx_rad)
    offset_y_mm = _finite("offset_y_mm", offset_y_mm)
    offset_z_mm = _finite("offset_z_mm", offset_z_mm)
    dy = node_uy_mm - twist_rx_rad * offset_z_mm
    dz = node_uz_mm + twist_rx_rad * offset_y_mm
    return LateralDisplacement(dy, dz)


@dataclass
class SectionClearanceResult:
    x_mm: float
    shaft_absolute: LateralDisplacement
    housing_absolute: LateralDisplacement
    consumed_by_deflection_mm: float
    label: str = ""


@dataclass
class CriticalSectionClearanceResult:
    governing_section: SectionClearanceResult
    all_sections: list  # list[SectionClearanceResult] — для отчёта/аудита, не только максимум
    clearance: ClearanceCheck


def critical_section_clearance(
    sections: Sequence[SectionClearanceResult],
    *, housing_inner_diameter_mm: float, screw_outer_diameter_mm: float,
    runout_mm: float = 0.0, manufacturing_tolerance_mm: float = 0.0, wear_allowance_mm: float = 0.0,
) -> CriticalSectionClearanceResult:
    """
    Выбирает ИЗ ЗАДАННОГО НАБОРА сечений (`sections` — обычно узлы, для
    которых есть и прогиб вала, и перемещение корпуса, см. докстринг
    модуля про честное ограничение) то, где расход зазора ЧИСТО ОТ
    ПРОГИБА максимален, и считает итоговый `ClearanceCheck` для НЕГО
    (биение/допуски/износ — независимы от выбора сечения, добавляются
    к максимуму, а не к каждому сечению отдельно).
    """
    if not sections:
        raise ShaftHousingClearanceError(
            "Пуст список сечений — нечего проверять (раздел задания: 'проверь критическое "
            "сечение по длине', а не одну произвольную точку)."
        )
    governing = max(sections, key=lambda s: s.consumed_by_deflection_mm)
    result = clearance_check(
        housing_inner_diameter_mm=housing_inner_diameter_mm,
        screw_outer_diameter_mm=screw_outer_diameter_mm,
        shaft_deflection_mm=governing.consumed_by_deflection_mm,
        runout_mm=runout_mm, manufacturing_tolerance_mm=manufacturing_tolerance_mm,
        wear_allowance_mm=wear_allowance_mm,
    )
    return CriticalSectionClearanceResult(governing_section=governing, all_sections=list(sections), clearance=result)


# ---------------------------------------------------------------------------
# Источники: тот же курс сопромата/деталей машин, что и core/shaft_beam_
# model.py::clearance_check — единственное отличие здесь в том, КАК получено
# число "прогиб, съедающий зазор" (совместный расчёт, а не подстановка).
# ---------------------------------------------------------------------------

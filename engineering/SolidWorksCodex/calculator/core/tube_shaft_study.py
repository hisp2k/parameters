# -*- coding: utf-8 -*-
"""
Исследовательский расчёт вала TUBE-SAND-001 (Issue #3, продолжение —
прочность). Это ИССЛЕДОВАНИЕ (раздел задания: "допустим исследовательский
результат, но не закрытая позиция выпуска"), НЕ подтверждённая проверка:

- Схема ДВУХ шарнирных радиальных опор (одна с осевой фиксацией) — прямо
  названная в задании ПРЕДВАРИТЕЛЬНОЙ гипотезой для исследования, а не
  фактом эскиза. Расстояние между опорами здесь = подтверждённая длина по
  оси эскиза (2515 мм, п.3) — тоже ДОПУЩЕНИЕ (эскиз подтверждает расстояние
  между загрузкой/выгрузкой вдоль оси, а не координаты подшипников).
- Сечение вала (диаметр/толщина стенки), материал, реальная погонная масса
  винта/продукта, положение и величина крутящего момента (расположение
  привода — В КОНФЛИКТЕ, текст против графики, см. tube_engineering.py) —
  НЕ подтверждены. Поэтому здесь считаются только ОТКЛИКИ НА ЕДИНИЧНЫЕ
  НАГРУЗКИ (коэффициенты влияния — Н, Н·мм на 1 Н или 1 Н/мм приложенной
  нагрузки), а не подставляются выдуманные числа сечения/массы. Как только
  появятся реальные величины, результат = коэффициент × реальная нагрузка —
  без переписывания модели (та же схема core/shaft_beam_model.py).

Результат ЭТОГО модуля НИКОГДА не попадает в StrengthItem.verifications и
не участвует в release_gate — см. Project.tube_shaft_study (отдельное поле,
не часть strength_registry) и test_tube_shaft_study.py::
test_shaft_study_never_affects_release_gate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from calculator.core.shaft_beam_model import (
    PLANE_VERTICAL, AxialLoad, BeamLoadCase, DistributedLoad, PointLoad, ShaftSupport,
    solve_reactions, solve_shear_moment,
)

# Гипотеза схемы опор (раздел задания: "Базовая гипотеза для исследования —
# две радиальные шарнирные опоры, одна с осевой фиксацией") — НЕ факт эскиза.
SUPPORT_SCHEME_ASSUMPTION = (
    "ДОПУЩЕНИЕ ДЛЯ ИССЛЕДОВАНИЯ (не факт эскиза): две радиальные шарнирные опоры "
    "по концам подтверждённой длины по оси (2515 мм, п.3 эскиза); опора у загрузки — "
    "с осевой фиксацией, опора у выгрузки — допускает осевое перемещение. Реальное "
    "число, координаты, тип и жёсткость опор конструктивно НЕ подтверждены."
)

SPAN_SOURCE_NOTE = (
    "Расстояние между опорами исследования ПРИНЯТО РАВНЫМ подтверждённой длине по "
    "оси эскиза (2515 мм, п.3) — это расстояние между загрузкой и выгрузкой, "
    "НЕ подтверждённые координаты подшипников. Реальный шаг опор может отличаться."
)


@dataclass
class GravityDecomposition:
    angle_deg: float
    scenario_label: str
    transverse_component_factor: float   # cos(angle) — доля веса поперёк оси (в плоскости изгиба)
    axial_component_factor: float        # sin(angle) — доля веса вдоль оси


def gravity_decomposition_for_scenarios(
    scenario_angle_deg: float, scenario_heights_angle_deg: float,
) -> list[GravityDecomposition]:
    """
    Раздел задания: "Разложи силы тяжести по местным осям для каждого угла".
    Оба сценария (A — угол эскиза 35°; B — угол, пересчитанный из заявленных
    высот пола при том же L=2515 мм) сохраняются РАЗДЕЛЬНО — ни один не
    выбирается автоматически (см. GeometryConflictReport).
    """
    out = []
    for label, angle in (("сценарий_A_угол_эскиза", scenario_angle_deg),
                         ("сценарий_B_угол_по_высотам", scenario_heights_angle_deg)):
        rad = math.radians(angle)
        out.append(GravityDecomposition(
            angle_deg=angle, scenario_label=label,
            transverse_component_factor=math.cos(rad), axial_component_factor=math.sin(rad),
        ))
    return out


@dataclass
class UnitLoadInfluenceCoefficients:
    """
    Отклики на ЕДИНИЧНУЮ нагрузку — коэффициенты влияния, НЕ реальные
    эксплуатационные результаты (раздел задания: "явно обозначь их как
    коэффициенты влияния"). Умножаются на реальную нагрузку, когда она
    появится, БЕЗ пересчёта схемы.
    """

    span_mm: float
    # Единичная равномерная нагрузка 1 Н/мм по всему пролёту (напр. заготовка
    # под собственный вес трубы+продукта на единицу длины):
    reaction_per_unit_udl_n: float          # реакция каждой опоры (Н) на 1 Н/мм
    moment_max_per_unit_udl_nmm: float      # максимальный момент (Н·мм) на 1 Н/мм, в середине пролёта
    # Единичная точечная нагрузка 1 Н в середине пролёта:
    reaction_per_unit_point_n: float
    moment_max_per_unit_point_nmm: float


def unit_load_influence_coefficients(span_mm: float) -> UnitLoadInfluenceCoefficients:
    """Строит BeamLoadCase по гипотезе опор выше и считает отклики на единичные нагрузки."""
    supports = [ShaftSupport(0.0, axially_fixed=True, label="опора_у_загрузки (допущение)"),
                ShaftSupport(span_mm, axially_fixed=False, label="опора_у_выгрузки (допущение)")]

    udl_case = BeamLoadCase(
        total_length_mm=span_mm, supports=supports,
        distributed_loads=[DistributedLoad(0.0, span_mm, 1.0, PLANE_VERTICAL, label="единичная_УДН")],
    )
    udl_reactions = solve_reactions(udl_case, PLANE_VERTICAL)
    udl_solution = solve_shear_moment(udl_case, PLANE_VERTICAL)
    udl_m_max = udl_solution.moment(span_mm / 2.0)

    point_case = BeamLoadCase(
        total_length_mm=span_mm, supports=supports,
        point_loads=[PointLoad(span_mm / 2.0, 1.0, PLANE_VERTICAL, label="единичная_сила")],
    )
    point_reactions = solve_reactions(point_case, PLANE_VERTICAL)
    point_solution = solve_shear_moment(point_case, PLANE_VERTICAL)
    point_m_max = point_solution.moment(span_mm / 2.0)

    return UnitLoadInfluenceCoefficients(
        span_mm=span_mm,
        reaction_per_unit_udl_n=udl_reactions.support_a_n,
        moment_max_per_unit_udl_nmm=udl_m_max,
        reaction_per_unit_point_n=point_reactions.support_a_n,
        moment_max_per_unit_point_nmm=point_m_max,
    )


@dataclass
class TubeShaftInfluenceStudy:
    """Полный исследовательский отчёт — НЕ VerificationRecord, НЕ участвует в release_gate."""

    is_exploratory: bool = True
    closes_release_gate_item: bool = False
    support_scheme_assumption: str = SUPPORT_SCHEME_ASSUMPTION
    span_source_note: str = SPAN_SOURCE_NOTE
    span_mm: float = 0.0
    gravity_decomposition: list[GravityDecomposition] = field(default_factory=list)
    influence_coefficients: Optional[UnitLoadInfluenceCoefficients] = None
    missing_for_real_result: list[str] = field(default_factory=list)
    drive_torque_path_note: str = ""

    def to_dict(self) -> dict:
        return {
            "is_exploratory": self.is_exploratory,
            "closes_release_gate_item": self.closes_release_gate_item,
            "support_scheme_assumption": self.support_scheme_assumption,
            "span_source_note": self.span_source_note,
            "span_mm": self.span_mm,
            "gravity_decomposition": [
                {
                    "angle_deg": g.angle_deg, "scenario_label": g.scenario_label,
                    "transverse_component_factor": g.transverse_component_factor,
                    "axial_component_factor": g.axial_component_factor,
                }
                for g in self.gravity_decomposition
            ],
            "influence_coefficients": (
                {
                    "span_mm": self.influence_coefficients.span_mm,
                    "reaction_per_unit_udl_n": self.influence_coefficients.reaction_per_unit_udl_n,
                    "moment_max_per_unit_udl_nmm": self.influence_coefficients.moment_max_per_unit_udl_nmm,
                    "reaction_per_unit_point_n": self.influence_coefficients.reaction_per_unit_point_n,
                    "moment_max_per_unit_point_nmm": self.influence_coefficients.moment_max_per_unit_point_nmm,
                }
                if self.influence_coefficients is not None else None
            ),
            "missing_for_real_result": self.missing_for_real_result,
            "drive_torque_path_note": self.drive_torque_path_note,
        }

    @staticmethod
    def from_dict(d: dict) -> "TubeShaftInfluenceStudy":
        ic = d.get("influence_coefficients")
        gd = [
            GravityDecomposition(
                angle_deg=g["angle_deg"], scenario_label=g["scenario_label"],
                transverse_component_factor=g["transverse_component_factor"],
                axial_component_factor=g["axial_component_factor"],
            )
            for g in d.get("gravity_decomposition", [])
        ]
        return TubeShaftInfluenceStudy(
            is_exploratory=d.get("is_exploratory", True),
            closes_release_gate_item=d.get("closes_release_gate_item", False),
            support_scheme_assumption=d.get("support_scheme_assumption", SUPPORT_SCHEME_ASSUMPTION),
            span_source_note=d.get("span_source_note", SPAN_SOURCE_NOTE),
            span_mm=d.get("span_mm", 0.0),
            gravity_decomposition=gd,
            influence_coefficients=(
                UnitLoadInfluenceCoefficients(**ic) if ic is not None else None
            ),
            missing_for_real_result=d.get("missing_for_real_result", []),
            drive_torque_path_note=d.get("drive_torque_path_note", ""),
        )


MISSING_FOR_REAL_SHAFT_RESULT = [
    "диаметр вала/трубы и толщина стенки (сечение) — методика для трубного шнека на ~35° отсутствует",
    "материал вала (модуль упругости E, плотность, предел текучести) — не подтверждён заказчиком",
    "реальная погонная масса винта+продукта на валу (нужна для перевода коэффициента влияния УДН в момент/Н·мм)",
    "фактическое число, координаты, тип и жёсткость опор (принята гипотеза 2 шарнирных опор по концам L=2515 мм)",
    "крутящий момент и его путь — расположение привода в конфликте (текст: нижний торец; графика: верхний торец)",
    "осевое усилие транспортирования — методика не подтверждена, не выводится из идеальной формулы без обоснования",
    "требуемая производительность/плотность/абразивность/крупность продукта — необходимы для нагрузок",
]


def build_tube_shaft_study(
    span_mm: float, scenario_angle_deg: float, scenario_heights_angle_deg: float,
) -> TubeShaftInfluenceStudy:
    """Собирает полный исследовательский отчёт по вALу TUBE-SAND-001 на подтверждённой длине по оси."""
    return TubeShaftInfluenceStudy(
        span_mm=span_mm,
        gravity_decomposition=gravity_decomposition_for_scenarios(scenario_angle_deg, scenario_heights_angle_deg),
        influence_coefficients=unit_load_influence_coefficients(span_mm),
        missing_for_real_result=list(MISSING_FOR_REAL_SHAFT_RESULT),
        drive_torque_path_note=(
            "Путь крутящего момента (привод → винт → продукт) НЕ рассчитан числом: расположение привода "
            "в конфликте (см. DriveLocationConflictReport) — точка приложения момента вдоль оси не "
            "зафиксирована ни в одном из двух источников одновременно."
        ),
    )

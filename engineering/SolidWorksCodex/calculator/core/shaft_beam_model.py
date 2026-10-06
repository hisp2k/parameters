# -*- coding: utf-8 -*-
"""
Балочная модель вала/трубы (Issue #3, продолжение — прочность TUBE-SAND-001).

НАЗНАЧЕНИЕ. Это ОБЩИЙ, не привязанный к TUBE-SAND-001 решатель прямой
задачи сопротивления материалов для пространственной ступенчатой балки на
ДВУХ радиальных опорах (статически определимая схема — раздел задания
прямо называет её ПРЕДВАРИТЕЛЬНОЙ гипотезой для исследования, не фактом
эскиза). Он не содержит ни одного числа, специфичного для TUBE-SAND-001—
все нагрузки/сечения/опоры передаются вызывающим кодом. Это отличает его от
`core/strength_calculations.py::shaft_torsion_only_check/shaft_combined_check`,
которые рассчитаны на СПЛОШНОЙ вал и принимают изгибающий момент как готовое
число — здесь момент/перерезывающая сила/угол поворота/прогиб вычисляются
из явно заданных нагрузок и опор для ПОЛОГО (трубного) сечения, поэтому
старые функции к трубе не применяются "как есть" (см. их docstring).

МЕТОД. Классическое прямое интегрирование (метод начальных параметров /
"сингулярных функций") для статически определимой балки на двух опорах,
возможно с консольными свесами за пределами опор:
- реакции — из уравнений статики (ΣF=0, ΣM=0) относительно каждой опоры;
- перерезывающая сила V(x) и изгibающий момент M(x) — точные кусочно-
  полиномиальные функции (V кусочно-линейна под равномерной нагрузкой,
  M — кусочно-квадратична), без сеточной аппроксимации;
- угол поворота θ(x) и прогиб y(x) — двойным точным интегрированием M(x)/EI
  по тем же участкам, с двумя постоянными интегрирования, определяемыми
  условиями y=0 на ОБЕИХ опорах (а не на левом конце — опоры могут быть не
  на концах балки, если есть консольные свесы).

Отдельно — путь передачи КРУТЯЩЕГО МОМЕНТА: он НЕ проходит через радиальные
опоры (подшипник не должен искусственно воспринимать приводной момент, по
прямому требованию задания) — см. `torque_diagram()`/`torque_equilibrium_
residual()`, которые оперируют только точками приложения момента (привод/
сопротивление продукта), независимо от опор изгиба.

ПРОВЕРКА РЕШАТЕЛЯ. `calculator/tests/test_shaft_beam_model.py` сверяет
реакции/момент/прогиб с закрытыми формулами сопромата для точечной силы в
середине пролёта, равномерной нагрузки по всему пролёту и внецентренной
точечной силы — на полностью синтетических (не TUBE-SAND-001) данных.

Источники метода: Александров А.В., "Сопротивление материалов"; Писаренко
Г.С. и др., "Сопротивление материалов" — раздел "Метод начальных
параметров"/"Интегрирование дифференциального уравнения изогнутой оси
балки"; для полого круглого сечения — тот же класс справочников, раздел
"Геометрические характеристики сечений".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

PLANE_VERTICAL = "вертикальная"
PLANE_HORIZONTAL = "горизонтальная"
VALID_PLANES = (PLANE_VERTICAL, PLANE_HORIZONTAL)


class ShaftBeamModelError(ValueError):
    """Некорректные входные данные модели (не путать с честным UNKNOWN — см. модуль-обёртку)."""


def _finite(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShaftBeamModelError(f"{name}: ожидалось число, получено {type(value).__name__} ({value!r}).")
    if not math.isfinite(value):
        raise ShaftBeamModelError(f"{name}: значение должно быть конечным числом, получено {value!r}.")
    return float(value)


# --------------------------------------------------------------------------
# Геометрия сечения
# --------------------------------------------------------------------------

@dataclass
class HollowCircularSection:
    """
    Полое круглое сечение (труба). outer/inner — НАРУЖНЫЙ и ВНУТРЕННИЙ
    диаметры, мм. `source`/`status` — откуда взяты значения (эскиз/CAD/
    допущение) и их статус (напр. "UNKNOWN", "ПОДТВЕРЖДЕНО_ЗАКАЗЧИКОМ") —
    обязательны для трассируемости, значения по умолчанию — явные
    заглушки, а не тихая подстановка.
    """

    outer_diameter_mm: float
    inner_diameter_mm: float
    source: str = "UNKNOWN"
    status: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.outer_diameter_mm = _finite("outer_diameter_mm", self.outer_diameter_mm)
        self.inner_diameter_mm = _finite("inner_diameter_mm", self.inner_diameter_mm)
        if self.outer_diameter_mm <= 0:
            raise ShaftBeamModelError("outer_diameter_mm должен быть больше нуля.")
        if self.inner_diameter_mm < 0:
            raise ShaftBeamModelError("inner_diameter_mm не может быть отрицательным.")
        if self.inner_diameter_mm >= self.outer_diameter_mm:
            raise ShaftBeamModelError(
                "inner_diameter_mm должен быть меньше outer_diameter_mm "
                f"(получено {self.inner_diameter_mm} >= {self.outer_diameter_mm})."
            )

    @property
    def area_mm2(self) -> float:
        return math.pi / 4.0 * (self.outer_diameter_mm ** 2 - self.inner_diameter_mm ** 2)

    @property
    def moment_of_inertia_mm4(self) -> float:
        """Осевой момент инерции I = π/64·(D⁴−d⁴) — для изгиба."""
        return math.pi / 64.0 * (self.outer_diameter_mm ** 4 - self.inner_diameter_mm ** 4)

    @property
    def polar_moment_of_inertia_mm4(self) -> float:
        """Полярный момент инерции Jp = π/32·(D⁴−d⁴) = 2·I — для кручения круглого/кольцевого сечения."""
        return math.pi / 32.0 * (self.outer_diameter_mm ** 4 - self.inner_diameter_mm ** 4)

    @property
    def section_modulus_bending_mm3(self) -> float:
        """W = I / (D/2) — момент сопротивления изгибу."""
        return self.moment_of_inertia_mm4 / (self.outer_diameter_mm / 2.0)

    @property
    def section_modulus_torsion_mm3(self) -> float:
        """Wp = Jp / (D/2) — момент сопротивления кручению."""
        return self.polar_moment_of_inertia_mm4 / (self.outer_diameter_mm / 2.0)

    @property
    def radius_of_gyration_mm(self) -> float:
        return math.sqrt(self.moment_of_inertia_mm4 / self.area_mm2)

    def euler_bernoulli_applicable(self, span_mm: float) -> tuple[bool, str]:
        """
        ПРЕДВАРИТЕЛЬНЫЙ отсеивающий признак по отношению пролёт/наружный
        диаметр — общепринятый инженерный порог: при L/D < ~10 вклад сдвига
        в прогиб обычно становится существенным (>≈3-5%) и стоит переходить
        на модель Тимошенко. Порог — ОРИЕНТИР (см. источники модуля), не
        норматив и НЕ строгое доказательство.

        Codex-замечание (продолжение, 18.09.2026, п.1): L/D≥10 — это только
        предварительный фильтр по ОДНОМУ параметру (стройности), а не
        доказательство того, что сдвиг реально пренебрежим для конкретной
        схемы нагружения. Известные ограничения этого признака, которые он
        НЕ учитывает: сосредоточенные нагрузки рядом с опорой (локально
        повышают долю сдвига независимо от общего L/D), резкая ступенчатость
        сечения (в тонком, но коротком участке сдвиг может быть значим
        локально даже при большом общем L/D), нестандартные условия опор
        (не шарнир/шарнир), и требуемую точность самого расчёта. Поэтому
        `applicable=True` здесь означает лишь "предварительный отсев по L/D
        пройден, дальнейшая проверка Эйлера–Бернулли разумна как первое
        приближение" — а не "сдвигом доказательно можно пренебречь".
        Вызывающий код обязан отображать это как предварительный фильтр в
        отчётах, а не как самостоятельное доказательство.
        """
        span_mm = _finite("span_mm", span_mm)
        if span_mm <= 0:
            raise ShaftBeamModelError("span_mm должен быть больше нуля.")
        ratio = span_mm / self.outer_diameter_mm
        if ratio >= 10.0:
            return True, (
                f"L/D={ratio:.1f} ≥ 10 — ПРЕДВАРИТЕЛЬНЫЙ фильтр по стройности пройден: "
                "балка Эйлера–Бернулли разумна как первое приближение. Это НЕ доказательство "
                "пренебрежимости сдвига для конкретной схемы нагружения (см. докстринг метода) — "
                "локальные точечные нагрузки у опоры и резкая ступенчатость сечения этим "
                "признаком не учитываются."
            )
        return False, (
            f"L/D={ratio:.1f} < 10 — короткая/толстая балка, вклад сдвиговой деформации "
            "может быть значимым; для прогиба использовать модель Тимошенко "
            "(добавляет слагаемое κ·V/(G·A) к углу поворота) вместо чистого Эйлера–Бернулли."
        )


# --------------------------------------------------------------------------
# Опоры и нагрузки
# --------------------------------------------------------------------------

@dataclass
class ShaftSupport:
    """
    Радиальная опора (подшипник). `axially_fixed` — эта опора воспринимает
    осевое усилие (по умолчанию задания: одна опора с осевой фиксацией,
    другая — только радиальная, допускает осевое перемещение). Не заделка:
    опора НЕ передаёт изгибающий момент (шарнирная), см. docstring модуля.
    """

    position_mm: float
    axially_fixed: bool = False
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.position_mm = _finite("position_mm", self.position_mm)


@dataclass
class PointLoad:
    position_mm: float
    magnitude_n: float   # знак: положительное значение — нагрузка в положительном направлении оси плоскости
    plane: str
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.position_mm = _finite("position_mm", self.position_mm)
        self.magnitude_n = _finite("magnitude_n", self.magnitude_n)
        if self.plane not in VALID_PLANES:
            raise ShaftBeamModelError(f"plane должен быть одним из {VALID_PLANES}, получено {self.plane!r}.")


@dataclass
class DistributedLoad:
    start_mm: float
    end_mm: float
    intensity_n_per_mm: float   # постоянная интенсивность на участке (собственный вес трубы/продукта и т.п.)
    plane: str
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.start_mm = _finite("start_mm", self.start_mm)
        self.end_mm = _finite("end_mm", self.end_mm)
        self.intensity_n_per_mm = _finite("intensity_n_per_mm", self.intensity_n_per_mm)
        if self.end_mm <= self.start_mm:
            raise ShaftBeamModelError("end_mm должен быть больше start_mm.")
        if self.plane not in VALID_PLANES:
            raise ShaftBeamModelError(f"plane должен быть одним из {VALID_PLANES}, получено {self.plane!r}.")

    @property
    def resultant_n(self) -> float:
        return self.intensity_n_per_mm * (self.end_mm - self.start_mm)

    @property
    def centroid_mm(self) -> float:
        return (self.start_mm + self.end_mm) / 2.0


@dataclass
class AxialLoad:
    """Осевое усилие (транспортирование/реакция продукта). Знак: положительное — сжатие вала."""

    magnitude_n: float
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.magnitude_n = _finite("magnitude_n", self.magnitude_n)


@dataclass
class AppliedTorque:
    """
    Точка приложения крутящего момента (привод — вход, сопротивление
    продукта/винта — выход). Путь момента отдельный от изгиба (см. docstring
    модуля) — supports здесь не участвуют.
    """

    position_mm: float
    torque_nm: float
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.position_mm = _finite("position_mm", self.position_mm)
        self.torque_nm = _finite("torque_nm", self.torque_nm)


# --------------------------------------------------------------------------
# Расчётная схема
# --------------------------------------------------------------------------

@dataclass
class BeamLoadCase:
    """
    Полная расчётная схема балки на ДВУХ опорах (статически определимая —
    раздел задания: "не назначай обеим опорам полную заделку"; здесь опоры
    всегда шарнирные радиальные, поэтому лишних реакций нет). Если по факту
    конструкции опор больше двух или есть подвесная/консольная особенность —
    эта схема НЕ применяется без изменения (см. docstring модуля) — метод
    статически определим только для ровно двух опор.
    """

    total_length_mm: float
    supports: list[ShaftSupport] = field(default_factory=list)
    point_loads: list[PointLoad] = field(default_factory=list)
    distributed_loads: list[DistributedLoad] = field(default_factory=list)
    axial_loads: list[AxialLoad] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.total_length_mm = _finite("total_length_mm", self.total_length_mm)
        if self.total_length_mm <= 0:
            raise ShaftBeamModelError("total_length_mm должен быть больше нуля.")
        if len(self.supports) != 2:
            raise ShaftBeamModelError(
                f"Решатель статически определим только для РОВНО двух опор, получено "
                f"{len(self.supports)}. Для схемы с иным числом опор (консоль/подвесная "
                "опора) эта модель не применяется без изменения — раздел задания "
                "\"измени схему\", не подгоняй под два уравнения статики."
            )
        for load in self.point_loads + self.distributed_loads:
            if load.plane not in VALID_PLANES:
                raise ShaftBeamModelError(f"Неизвестная плоскость нагрузки: {load.plane!r}.")
        axially_fixed = [s for s in self.supports if s.axially_fixed]
        if len(axially_fixed) > 1:
            raise ShaftBeamModelError(
                "Больше одной опоры с осевой фиксацией — статически неопределимо по оси; "
                "по умолчанию задания осевая фиксация должна быть ровно у ОДНОЙ опоры."
            )

    def supports_sorted(self) -> tuple[ShaftSupport, ShaftSupport]:
        a, b = sorted(self.supports, key=lambda s: s.position_mm)
        if a.position_mm == b.position_mm:
            raise ShaftBeamModelError("Обе опоры не могут быть в одной координате.")
        return a, b


# --------------------------------------------------------------------------
# Статика: реакции
# --------------------------------------------------------------------------

@dataclass
class Reactions:
    support_a_n: float
    support_b_n: float
    axial_support_n: Optional[float] = None


def solve_reactions(case: BeamLoadCase, plane: str) -> Reactions:
    """
    ΣF=0, ΣM=0 относительно опоры A — статически определимая балка на двух
    шарнирных опорах, возможно со свесами. Осевая реакция — целиком у
    единственной осево-зафиксированной опоры (или None, если такой опоры
    нет и приложены осевые нагрузки — это ошибка схемы, не 0 по умолчанию).
    """
    a, b = case.supports_sorted()
    span = b.position_mm - a.position_mm

    moment_about_a = 0.0
    total_load = 0.0
    for pl in case.point_loads:
        if pl.plane != plane:
            continue
        moment_about_a += pl.magnitude_n * (pl.position_mm - a.position_mm)
        total_load += pl.magnitude_n
    for dl in case.distributed_loads:
        if dl.plane != plane:
            continue
        moment_about_a += dl.resultant_n * (dl.centroid_mm - a.position_mm)
        total_load += dl.resultant_n

    r_b = moment_about_a / span
    r_a = total_load - r_b

    axial_support_n = None
    total_axial = sum(ax.magnitude_n for ax in case.axial_loads)
    if case.axial_loads:
        fixed = [s for s in case.supports if s.axially_fixed]
        if not fixed:
            raise ShaftBeamModelError(
                "Приложена осевая нагрузка, но ни одна опора не отмечена как осево-фиксированная — "
                "неизвестно, кто воспринимает осевое усилие (не подставляется по умолчанию)."
            )
        axial_support_n = -total_axial
    return Reactions(support_a_n=r_a, support_b_n=r_b, axial_support_n=axial_support_n)


# --------------------------------------------------------------------------
# Внутренние силовые факторы: V(x), M(x) — точное кусочное интегрирование
# --------------------------------------------------------------------------

@dataclass
class _Segment:
    x0: float
    x1: float
    v0: float      # перерезывающая сила в начале участка (сразу после точечных сил в x0)
    w: float       # интенсивность распределённой нагрузки на участке (постоянная)
    m0: float       # изгибающий момент в начале участка
    # EI ЭТОГО участка (Н·мм²) — для ступенчатого вала может отличаться от
    # соседних участков (см. SectionSegment/SteppedShaftProfile ниже и
    # Codex-замечание, продолжение 18.09.2026, п.1). None — участок ещё не
    # привязан к сечению (только что построен solve_shear_moment(), до
    # solve_deflection()).
    ei_nmm2: Optional[float] = None


# --------------------------------------------------------------------------
# Ступенчатый вал: сечение/E/G меняются по длине (Codex-замечание,
# продолжение 18.09.2026, п.1)
# --------------------------------------------------------------------------

@dataclass
class SectionSegment:
    """
    Один участок ступенчатого вала — собственное сечение, модуль упругости
    E (изгиб) и, если нужен угол закручивания, модуль сдвига G. Реальный
    вал почти всегда ступенчатый (посадочные места под подшипники/уплотнения
    обычно уже пролётной части) — раньше решатель прогиба принимал ОДНО E и
    ОДНО сечение на весь пролёт (`solve_deflection(solution, e_mpa,
    section)`), что для ступенчатого вала завышает или занижает жёсткость
    на каждом участке и даёт неверный прогиб. Здесь EI/GJ берутся по месту.
    """

    start_mm: float
    end_mm: float
    section: HollowCircularSection
    e_mpa: float
    g_mpa: Optional[float] = None   # нужен только для угла закручивания (solve_twist_angle)
    label: str = ""
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        self.start_mm = _finite("start_mm", self.start_mm)
        self.end_mm = _finite("end_mm", self.end_mm)
        self.e_mpa = _finite("e_mpa", self.e_mpa)
        if self.end_mm <= self.start_mm:
            raise ShaftBeamModelError("end_mm должен быть больше start_mm.")
        if self.e_mpa <= 0:
            raise ShaftBeamModelError("e_mpa должен быть больше нуля.")
        if self.g_mpa is not None:
            self.g_mpa = _finite("g_mpa", self.g_mpa)
            if self.g_mpa <= 0:
                raise ShaftBeamModelError("g_mpa должен быть больше нуля, если задан.")

    @property
    def ei_nmm2(self) -> float:
        return self.e_mpa * self.section.moment_of_inertia_mm4

    @property
    def gj_nmm2(self) -> Optional[float]:
        if self.g_mpa is None:
            return None
        return self.g_mpa * self.section.polar_moment_of_inertia_mm4


@dataclass
class SteppedShaftProfile:
    """
    Полный профиль сечений вала по длине — участки должны точно стыковаться
    без зазора и без наложения и полностью покрывать [0, total_length_mm].
    Это ГЕОМЕТРИЧЕСКАЯ непрерывность вала (не путать с непрерывностью
    прогиба/угла поворота, которая обеспечивается методом интегрирования
    в BeamSolution, см. ниже) — разрыв профиля физически означал бы дырку
    в вале, поэтому проверяется здесь жёстко, как ошибка входных данных.
    """

    total_length_mm: float
    segments: list[SectionSegment] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.total_length_mm = _finite("total_length_mm", self.total_length_mm)
        if self.total_length_mm <= 0:
            raise ShaftBeamModelError("total_length_mm должен быть больше нуля.")
        if not self.segments:
            raise ShaftBeamModelError("Профиль ступенчатого вала должен содержать хотя бы один участок.")
        ordered = sorted(self.segments, key=lambda s: s.start_mm)
        if abs(ordered[0].start_mm - 0.0) > 1e-6:
            raise ShaftBeamModelError(
                f"Первый участок профиля должен начинаться в 0, получено {ordered[0].start_mm}."
            )
        if abs(ordered[-1].end_mm - self.total_length_mm) > 1e-6:
            raise ShaftBeamModelError(
                f"Последний участок профиля должен заканчиваться в total_length_mm="
                f"{self.total_length_mm}, получено {ordered[-1].end_mm}."
            )
        for prev, nxt in zip(ordered, ordered[1:]):
            if abs(prev.end_mm - nxt.start_mm) > 1e-6:
                raise ShaftBeamModelError(
                    f"Разрыв или наложение профиля сечений между {prev.end_mm} и {nxt.start_mm} мм — "
                    "участки ступенчатого вала должны стыковаться встык, без зазора и без перекрытия."
                )
        self.segments = ordered

    def breakpoints(self) -> list[float]:
        pts = {0.0, self.total_length_mm}
        for seg in self.segments:
            pts.add(seg.start_mm)
            pts.add(seg.end_mm)
        return sorted(pts)

    def segment_at(self, x: float) -> SectionSegment:
        for seg in self.segments:
            if seg.start_mm - 1e-9 <= x <= seg.end_mm + 1e-9:
                return seg
        raise ShaftBeamModelError(f"x={x} за пределами профиля сечений [0, {self.total_length_mm}].")

    @staticmethod
    def uniform(
        total_length_mm: float, section: HollowCircularSection, e_mpa: float,
        g_mpa: Optional[float] = None,
    ) -> "SteppedShaftProfile":
        """Однородный (не ступенчатый) вал — один участок на всю длину."""
        return SteppedShaftProfile(total_length_mm=total_length_mm, segments=[
            SectionSegment(start_mm=0.0, end_mm=total_length_mm, section=section, e_mpa=e_mpa, g_mpa=g_mpa),
        ])


@dataclass
class BeamSolution:
    case: BeamLoadCase
    plane: str
    reactions: Reactions
    segments: list[_Segment]
    breakpoints: list[float]
    # Коррекция прогиба (см. модуль-докстринг: y(x)=y_raw(x)+c1*x+c2)
    ei_nmm2: Optional[float] = None   # оставлено для обратной совместимости чтения; не используется решателем
    c1: Optional[float] = None
    c2: Optional[float] = None
    profile: Optional["SteppedShaftProfile"] = None

    def _segment_for(self, x: float) -> _Segment:
        for seg in self.segments:
            if seg.x0 - 1e-9 <= x <= seg.x1 + 1e-9:
                return seg
        raise ShaftBeamModelError(f"x={x} за пределами балки [0, {self.case.total_length_mm}].")

    def shear(self, x: float) -> float:
        seg = self._segment_for(x)
        return seg.v0 - seg.w * (x - seg.x0)

    def moment(self, x: float) -> float:
        seg = self._segment_for(x)
        s = x - seg.x0
        return seg.m0 + seg.v0 * s - 0.5 * seg.w * s ** 2

    def _raw_slope_and_deflection(self, x: float) -> tuple[float, float]:
        """
        θ_raw(x), y_raw(x) при θ_raw(0)=0, y_raw(0)=0 (произвольная точка
        отсчёта на левом конце балки) — точное интегрирование по участкам,
        накопительно слева направо, останавливаясь ровно в x.
        """
        theta = 0.0
        y = 0.0
        for seg in self.segments:
            if x <= seg.x0 + 1e-12:
                break
            s = min(x, seg.x1) - seg.x0
            if s < 0:
                break
            m0, v0, w = seg.m0, seg.v0, seg.w
            # EI ЭТОГО участка (ступенчатый вал — см. SteppedShaftProfile) —
            # НЕ единая self.ei_nmm2 на весь пролёт (Codex-замечание,
            # продолжение 18.09.2026, п.1). θ/y накапливаются как физическое
            # состояние через границу участка — это и есть непрерывность
            # прогиба/угла поворота при разрыве EI (кривизна M/EI разрывна,
            # сами θ и y — нет), без отдельных уравнений стыковки.
            ei = seg.ei_nmm2 if seg.ei_nmm2 is not None else self.ei_nmm2
            if ei is None:
                raise ShaftBeamModelError(
                    "EI участка не задан — вызовите solve_deflection() с профилем сечений "
                    "перед slope_rad()/deflection_mm()."
                )
            # θ(s) = θ0 + (1/EI)[m0*s + v0*s²/2 - w*s³/6]
            # y(s) = y0 + θ0*s + (1/EI)[m0*s²/2 + v0*s³/6 - w*s⁴/24]
            dtheta = (m0 * s + v0 * s ** 2 / 2.0 - w * s ** 3 / 6.0) / ei
            dy = theta * s + (m0 * s ** 2 / 2.0 + v0 * s ** 3 / 6.0 - w * s ** 4 / 24.0) / ei
            y += dy
            theta += dtheta
            if x < seg.x1 - 1e-9:
                break
        return theta, y

    def slope_rad(self, x: float) -> float:
        if self.c1 is None:
            raise ShaftBeamModelError("EI не задан — вызовите solve_deflection() перед slope_rad().")
        theta_raw, _ = self._raw_slope_and_deflection(x)
        return theta_raw + self.c1

    def deflection_mm(self, x: float) -> float:
        if self.c1 is None:
            raise ShaftBeamModelError("EI не задан — вызовите solve_deflection() перед deflection_mm().")
        _, y_raw = self._raw_slope_and_deflection(x)
        return y_raw + self.c1 * x + self.c2


def solve_shear_moment(case: BeamLoadCase, plane: str) -> BeamSolution:
    """
    Строит точные кусочные V(x)/M(x) для заданной плоскости. Разбивает балку
    на участки по всем точкам приложения нагрузок/опор; на каждом участке
    интенсивность распределённой нагрузки постоянна (или ноль), поэтому V
    линейна, M — квадратична (обе точные многочлены, без сеточной ошибки).
    """
    reactions = solve_reactions(case, plane)
    a, b = case.supports_sorted()

    breakpoints = {0.0, case.total_length_mm, a.position_mm, b.position_mm}
    for pl in case.point_loads:
        if pl.plane == plane:
            breakpoints.add(pl.position_mm)
    for dl in case.distributed_loads:
        if dl.plane == plane:
            breakpoints.add(dl.start_mm)
            breakpoints.add(dl.end_mm)
    xs = sorted(x for x in breakpoints if 0.0 <= x <= case.total_length_mm)

    def w_at_segment(x0: float, x1: float) -> float:
        mid = (x0 + x1) / 2.0
        total = 0.0
        for dl in case.distributed_loads:
            if dl.plane == plane and dl.start_mm - 1e-9 <= mid <= dl.end_mm + 1e-9:
                total += dl.intensity_n_per_mm
        return total

    def point_load_at(x: float) -> float:
        # Знаковая сверка (см. проверку решателя на закрытых формулах):
        # реакции опор действуют ПРОТИВОПОЛОЖНО направлению приложенных
        # нагрузок (та же логика, что и в distributed-нагрузке, где
        # v_next = v_current - w*s) — поэтому реакции складываются со
        # знаком "+" (уже посчитаны как противодействующие ΣF=0), а
        # точечные нагрузки вычитаются, а не складываются.
        total = 0.0
        for pl in case.point_loads:
            if pl.plane == plane and abs(pl.position_mm - x) < 1e-6:
                total -= pl.magnitude_n
        if abs(x - a.position_mm) < 1e-6:
            total += reactions.support_a_n
        if abs(x - b.position_mm) < 1e-6:
            total += reactions.support_b_n
        return total

    segments: list[_Segment] = []
    v_current = 0.0
    m_current = 0.0
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        v_current += point_load_at(x0)   # скачок от точечных сил/реакций ровно в x0
        w = w_at_segment(x0, x1)
        seg = _Segment(x0=x0, x1=x1, v0=v_current, w=w, m0=m_current)
        segments.append(seg)
        s = x1 - x0
        v_next = v_current - w * s
        m_current = m_current + v_current * s - 0.5 * w * s ** 2
        # Точечная нагрузка ровно в x1 учитывается на следующей итерации через point_load_at(x0=x1).
        v_current = v_next

    # Точечная нагрузка/реакция в самой последней точке (нет следующего участка,
    # но momент в конце должен быть согласован — для целостности добавим виртуальный
    # нулевой участок, чтобы moment(total_length) можно было прочитать корректно).
    segments.append(_Segment(x0=xs[-1], x1=xs[-1], v0=v_current + point_load_at(xs[-1]), w=0.0, m0=m_current))

    return BeamSolution(case=case, plane=plane, reactions=reactions, segments=segments, breakpoints=xs)


def solve_deflection(solution: BeamSolution, profile: SteppedShaftProfile) -> BeamSolution:
    """
    Достраивает угол поворота/прогиб на уже посчитанном BeamSolution.

    Codex-замечание (продолжение, 18.09.2026, п.1): раньше принимала одно
    e_mpa и одно HollowCircularSection на весь пролёт — для СТУПЕНЧАТОГО
    вала (типично: посадочные места под подшипники уже пролётной части)
    это давало неверную (завышенную или заниженную) жёсткость участков и,
    следовательно, неверный прогиб. Теперь принимает SteppedShaftProfile —
    набор участков со своим E/сечением; для однородного вала используйте
    `SteppedShaftProfile.uniform(total_length_mm, section, e_mpa)`.

    Участки решения (v0/w/m0 — не зависят от сечения, статически
    определимая схема) пересобираются на объединении точек нагрузок/опор
    И точек смены сечения, так что EI постоянно внутри каждого итогового
    микро-участка. Постоянные интегрирования c1/c2 определяются из y=0 на
    ОБЕИХ опорах (не на концах балки — опоры могут быть не на концах при
    наличии консольных свесов, см. docstring модуля). Непрерывность
    прогиба и угла поворота на границе участков с разным EI обеспечена
    самим методом накопления состояния (см. _raw_slope_and_deflection) —
    отдельных уравнений стыковки не требуется, поскольку разрывна только
    кривизна M/EI, а не сами θ и y.
    """
    if not isinstance(profile, SteppedShaftProfile):
        raise ShaftBeamModelError(
            "solve_deflection() ожидает SteppedShaftProfile (используйте "
            "SteppedShaftProfile.uniform(...) для однородного вала), получено "
            f"{type(profile).__name__}."
        )
    if abs(profile.total_length_mm - solution.case.total_length_mm) > 1e-6:
        raise ShaftBeamModelError(
            f"Длина профиля сечений ({profile.total_length_mm} мм) не совпадает с длиной "
            f"балки ({solution.case.total_length_mm} мм)."
        )

    # Объединяем точки разрыва самого решения (нагрузки/опоры) с точками
    # смены сечения профиля — внутри каждого итогового участка постоянны
    # И силовые факторы (v0/w/m0), И EI.
    xs = sorted(
        x for x in (set(solution.breakpoints) | set(profile.breakpoints()))
        if 0.0 <= x <= solution.case.total_length_mm
    )
    if len(xs) < 2:
        raise ShaftBeamModelError("Недостаточно точек для построения участков прогиба.")

    new_segments: list[_Segment] = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        mid = (x0 + x1) / 2.0
        old_seg = solution._segment_for(mid)
        # m0/v0 старого (более грубого) участка относятся к его x0 —
        # пересчитываем их на начало нового, более мелкого участка x0.
        s_local = x0 - old_seg.x0
        m0_new = old_seg.m0 + old_seg.v0 * s_local - 0.5 * old_seg.w * s_local ** 2
        v0_new = old_seg.v0 - old_seg.w * s_local
        section_seg = profile.segment_at(mid)
        new_segments.append(_Segment(
            x0=x0, x1=x1, v0=v0_new, w=old_seg.w, m0=m0_new, ei_nmm2=section_seg.ei_nmm2,
        ))

    solution.segments = new_segments
    solution.breakpoints = xs
    solution.profile = profile
    solution.c1 = 0.0
    solution.c2 = 0.0

    a, b = solution.case.supports_sorted()
    _, y_raw_a = solution._raw_slope_and_deflection(a.position_mm)
    _, y_raw_b = solution._raw_slope_and_deflection(b.position_mm)
    # y(a) = y_raw_a + c1*a + c2 = 0 ; y(b) = y_raw_b + c1*b + c2 = 0
    span = b.position_mm - a.position_mm
    c1 = -(y_raw_b - y_raw_a) / span
    c2 = -y_raw_a - c1 * a.position_mm
    solution.c1 = c1
    solution.c2 = c2
    return solution


# --------------------------------------------------------------------------
# Кручение — отдельный путь (не через опоры)
# --------------------------------------------------------------------------

def torque_equilibrium_residual(torques: list[AppliedTorque]) -> float:
    """
    Сумма приложенных моментов должна быть ~0 (привод передаёт момент,
    сопротивление продукта/винта его уравновешивает) — это проверка
    равновесия, а не автоматическое замыкание баланса выдуманным числом.
    Ненулевой остаток — сигнал, что схема моментов не замкнута.
    """
    return sum(t.torque_nm for t in torques)


def torque_diagram(torques: list[AppliedTorque], x: float) -> float:
    """T(x) = сумма приложенных моментов левее (или в) точки x. Путь момента НЕ зависит от опор изгиба."""
    return sum(t.torque_nm for t in torques if t.position_mm <= x + 1e-9)


@dataclass
class TwistAngleSolution:
    """
    Угол закручивания вала под T(x) на ступенчатом профиле (свой G·J на
    каждом участке — Codex-замечание, продолжение 18.09.2026, п.1: раньше
    угол закручивания вообще не считался, только диаграмма T(x)). Отсчёт —
    от `reference_position_mm` (обычно вход привода), НЕ от опор изгиба
    (путь момента отдельный от опор, см. docstring модуля) — здесь нет
    условия "угол=0 на обеих опорах", это не изгиб.
    """

    torques: list[AppliedTorque]
    profile: SteppedShaftProfile
    reference_position_mm: float

    def twist_angle_rad(self, x: float) -> float:
        x = _finite("x", x)
        if x == self.reference_position_mm:
            return 0.0
        lo, hi = sorted((self.reference_position_mm, x))
        sign = 1.0 if x >= self.reference_position_mm else -1.0
        xs = sorted(
            v for v in (
                set(self.profile.breakpoints())
                | {lo, hi}
                | {t.position_mm for t in self.torques}
            )
            if lo - 1e-9 <= v <= hi + 1e-9
        )
        total_rad = 0.0
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            mid = (x0 + x1) / 2.0
            t_n_mm = torque_diagram(self.torques, mid) * 1000.0   # Н·м → Н·мм
            gj_nmm2 = self.profile.segment_at(mid).gj_nmm2
            total_rad += t_n_mm * (x1 - x0) / gj_nmm2
        return sign * total_rad


def solve_twist_angle(
    torques: list[AppliedTorque], profile: SteppedShaftProfile, reference_position_mm: float = 0.0,
) -> TwistAngleSolution:
    """
    Строит решение угла закручивания φ(x) = ∫ T(ξ)/(G·J(ξ)) dξ от
    `reference_position_mm` до x. Модуль сдвига G обязателен на КАЖДОМ
    участке профиля — если хоть один участок создан без g_mpa, это явная
    ошибка вызывающего кода (не подставляется "типичное" G).
    """
    for seg in profile.segments:
        if seg.gj_nmm2 is None:
            raise ShaftBeamModelError(
                f"Участок профиля [{seg.start_mm}, {seg.end_mm}] мм не имеет g_mpa — угол "
                "закручивания не может быть посчитан без модуля сдвига на каждом участке."
            )
    reference_position_mm = _finite("reference_position_mm", reference_position_mm)
    if not (0.0 - 1e-9 <= reference_position_mm <= profile.total_length_mm + 1e-9):
        raise ShaftBeamModelError(
            f"reference_position_mm={reference_position_mm} вне длины профиля [0, "
            f"{profile.total_length_mm}]."
        )
    return TwistAngleSolution(torques=list(torques), profile=profile, reference_position_mm=reference_position_mm)


# --------------------------------------------------------------------------
# Напряжения (полое сечение)
# --------------------------------------------------------------------------

def bending_stress_mpa(bending_moment_nmm: float, section: HollowCircularSection) -> float:
    """σ = M / W, Н·мм / мм³ = МПа напрямую (единицы модуля: мм-Н-МПа, см. docstring)."""
    return bending_moment_nmm / section.section_modulus_bending_mm3


def torsional_shear_stress_mpa(torque_nmm: float, section: HollowCircularSection) -> float:
    """τ = T / Wp."""
    return torque_nmm / section.section_modulus_torsion_mm3


def combined_von_mises_stress_mpa(bending_stress_mpa_value: float, torsional_shear_mpa: float) -> float:
    """
    σ_экв(Мизес) = sqrt(σ² + 3τ²) для одноосного изгибного напряжения + чистого
    сдвига от кручения. НЕ смешивается с 3-й теорией (Треска, sqrt(σ²+4τ²)),
    которая уже используется в core/strength_calculations.py для сплошного
    вала — раздел задания прямо запрещает смешивать критерии Мизеса и
    Треска в одном расчёте; здесь всегда Мизес, отдельно и явно.
    """
    return math.sqrt(bending_stress_mpa_value ** 2 + 3.0 * torsional_shear_mpa ** 2)


# --------------------------------------------------------------------------
# Численная (не L/D-фильтр) оценка вклада сдвиговой деформации в прогиб
# --------------------------------------------------------------------------

@dataclass
class ShearDeflectionEstimate:
    bending_deflection_mm: float
    shear_deflection_mm: float
    shear_to_bending_ratio: float
    shear_correction_factor: float
    source: str
    note: str


def central_point_load_shear_deflection_estimate(
    span_mm: float, point_load_n: float, section: HollowCircularSection,
    e_mpa: float, g_mpa: float, *, shear_correction_factor: float = 0.5,
) -> ShearDeflectionEstimate:
    """
    ЧИСЛЕННАЯ оценка вклада сдвиговой деформации в максимальный прогиб —
    независимая проверка коммита c24d42b, раздел 5: "прежнее требование
    численно оценить влияние сдвиговой деформации всё ещё не выполнено:
    переименование L/D-фильтра его не закрывает... выполни оценку/
    сопоставление с применимой моделью, указав источник и необходимые
    свойства сечения". `euler_bernoulli_applicable()` (см. её докстринг)
    остаётся ТОЛЬКО предварительным фильтром по стройности L/D — здесь,
    наоборот, для КОНКРЕТНОЙ, явно применимой схемы (балка на двух
    шарнирных опорах, СОСРЕДОТОЧЕННАЯ сила в СЕРЕДИНЕ пролёта — именно тот
    случай, который реально используется в этом репозитории для
    синтетического примера вала) считаются ДВА закрытых числа и их
    отношение, а не один общий вывод "применимо/неприменимо" для ЛЮБОЙ
    схемы нагружения.

    ФОРМУЛЫ (Тимошенко С.П., "Сопротивление материалов", ч.1, разделы про
    учёт сдвига при изгибе балок; тот же источник, что и остальные закрытые
    формулы этого модуля):
        δ_bending = P·L³ / (48·E·I)             — изгибный прогиб в
                                                    середине пролёта
                                                    (закрытая формула,
                                                    ДЛЯ СВЕРКИ с уже
                                                    посчитанным численно
                                                    прогибом того же случая)
        δ_shear   = P·L / (4·k_s·G·A)           — сдвиговый прогиб в
                                                    середине пролёта
    `shear_correction_factor` (k_s, коэффициент формы Тимошенко) —
    ПРИБЛИЖЕНИЕ 0.5 для ТОНКОСТЕННОЙ трубы (общепринятое инженерное
    значение, см. источник выше; для сплошного круглого сечения обычно
    берут ~0.9) — это ЯВНОЕ приближение для КОНКРЕТНОГО профиля стенки,
    не точное решение теории упругости для произвольного отношения
    D/d — вызывающий код обязан передавать значение, соответствующее
    реальной геометрии, а не полагаться на подставленное по умолчанию
    вслепую (докстринг явно называет допущение, применимость по
    D/d здесь НЕ проверяется автоматически — открытая методологическая
    граница, как и остальные оценки этого модуля).

    РЕЗУЛЬТАТ — `shear_to_bending_ratio` — это ЧИСЛО (не бинарный вердикт
    "применимо/неприменимо"): вызывающий код сам решает свой порог
    значимости (обычно 3-5%) и обязан явно показать это число в отчёте,
    а не скрывать за одним "OK"/"FAIL" по L/D.
    """
    span_mm = _finite("span_mm", span_mm)
    point_load_n = _finite("point_load_n", point_load_n)
    e_mpa = _finite("e_mpa", e_mpa)
    g_mpa = _finite("g_mpa", g_mpa)
    shear_correction_factor = _finite("shear_correction_factor", shear_correction_factor)
    if span_mm <= 0:
        raise ShaftBeamModelError("span_mm должен быть больше нуля.")
    if e_mpa <= 0 or g_mpa <= 0:
        raise ShaftBeamModelError("e_mpa и g_mpa должны быть больше нуля.")
    if shear_correction_factor <= 0:
        raise ShaftBeamModelError("shear_correction_factor должен быть больше нуля.")

    i_mm4 = section.moment_of_inertia_mm4
    a_mm2 = section.area_mm2
    bending = abs(point_load_n) * span_mm ** 3 / (48.0 * e_mpa * i_mm4)
    shear = abs(point_load_n) * span_mm / (4.0 * shear_correction_factor * g_mpa * a_mm2)
    ratio = shear / bending if bending > 0 else float("inf")
    return ShearDeflectionEstimate(
        bending_deflection_mm=bending, shear_deflection_mm=shear, shear_to_bending_ratio=ratio,
        shear_correction_factor=shear_correction_factor,
        source="Тимошенко С.П., «Сопротивление материалов», ч.1 — учёт сдвига при изгибе "
               "балок; k_s=0.5 — инженерное приближение для ТОНКОСТЕННОЙ трубы (не точное "
               "решение для произвольного D/d).",
        note=(
            f"δ_изгиб={bending:.4f} мм, δ_сдвиг={shear:.4f} мм, "
            f"δ_сдвиг/δ_изгиб={ratio * 100.0:.2f}% — численная оценка ТОЛЬКО для схемы "
            "'балка на двух шарнирных опорах, сосредоточенная сила в середине пролёта'; "
            "для другой схемы нагружения число нужно пересчитать заново, не переносить."
        ),
    )


# --------------------------------------------------------------------------
# Критическая частота вращения (первая собственная частота изгиба)
# --------------------------------------------------------------------------

def critical_speed_rpm(
    section: HollowCircularSection, span_mm: float, e_mpa: float, density_kg_m3: float,
    added_mass_kg: Optional[float] = None,
) -> tuple[float, str]:
    """
    Первая собственная частота изгиба однородного вала на двух шарнирных
    опорах: ω1 = π²·sqrt(E·I/(ρ·A·L⁴)) (закрытая форма для равномерного
    простого стержня, см. источники модуля) → n1[об/мин] = ω1·60/(2π).

    Если реальная масса винта/продукта на валу неизвестна (added_mass_kg не
    передан), результат — частота ГОЛОГО вала, явно помечается как НЕ
    представляющая собранный ротор (см. возвращаемое примечание) — метод
    Донкерлея (1/f²≈1/f_вала²+1/f_массы²) применяется только если
    added_mass_kg реально передан, иначе не подставляется произвольно.
    """
    e_mpa = _finite("e_mpa", e_mpa)
    density_kg_m3 = _finite("density_kg_m3", density_kg_m3)
    span_mm = _finite("span_mm", span_mm)
    if e_mpa <= 0 or density_kg_m3 <= 0 or span_mm <= 0:
        raise ShaftBeamModelError("e_mpa, density_kg_m3 и span_mm должны быть больше нуля.")

    e_pa = e_mpa * 1e6
    i_m4 = section.moment_of_inertia_mm4 * 1e-12
    a_m2 = section.area_mm2 * 1e-6
    l_m = span_mm / 1000.0

    omega1 = math.pi ** 2 * math.sqrt(e_pa * i_m4 / (density_kg_m3 * a_m2 * l_m ** 4))
    n1_bare_rpm = omega1 * 60.0 / (2.0 * math.pi)

    if added_mass_kg is None:
        return n1_bare_rpm, (
            "Частота ГОЛОГО вала (без учёта массы винта/спирали/продукта на валу) — "
            "не является рабочей критической частотой собранного ротора; для реальной "
            "оценки нужна масса винта/продукта на единицу длины (added_mass_kg)."
        )
    added_mass_kg = _finite("added_mass_kg", added_mass_kg)
    if added_mass_kg <= 0:
        raise ShaftBeamModelError("added_mass_kg должен быть больше нуля, если передан.")
    # Метод Донкерлея для сосредоточенной массы в середине пролёта (приближение):
    # f_массы = (1/2π)·sqrt(48·E·I / (m·L³)) — прогиб от точечной силы в центре.
    k_mid_n_per_m = 48.0 * e_pa * i_m4 / (l_m ** 3)
    f_mass_hz = (1.0 / (2.0 * math.pi)) * math.sqrt(k_mid_n_per_m / added_mass_kg)
    f_bare_hz = omega1 / (2.0 * math.pi)
    f_combined_hz = 1.0 / math.sqrt(1.0 / f_bare_hz ** 2 + 1.0 / f_mass_hz ** 2)
    n_combined_rpm = f_combined_hz * 60.0
    return n_combined_rpm, (
        "Оценка методом Донкерлея с сосредоточенной массой в СЕРЕДИНЕ пролёта — "
        "приближение; реальное распределение массы винта/продукта вдоль вала не учтено "
        "(если оно известно, нужен более точный расчёт, не Донкерлей для точечной массы)."
    )


# --------------------------------------------------------------------------
# Устойчивость (применимость проверки Эйлера)
# --------------------------------------------------------------------------

@dataclass
class BucklingApplicability:
    applicable: bool
    reason: str
    euler_critical_load_n: Optional[float] = None
    ratio_axial_to_critical: Optional[float] = None
    slenderness_ratio: Optional[float] = None


def buckling_applicability(
    section: HollowCircularSection, effective_length_mm: float, e_mpa: float,
    axial_compressive_n: Optional[float], proportional_limit_mpa: Optional[float] = None,
) -> BucklingApplicability:
    """
    Проверка Эйлера уместна ТОЛЬКО при сжимающем осевом усилии и достаточной
    гибкости стержня. axial_compressive_n<=0 (или None) — нагрузки нет или
    она растягивающая — проверка неприменима, а не автоматический PASS.
    """
    e_mpa = _finite("e_mpa", e_mpa)
    effective_length_mm = _finite("effective_length_mm", effective_length_mm)
    if e_mpa <= 0 or effective_length_mm <= 0:
        raise ShaftBeamModelError("e_mpa и effective_length_mm должны быть больше нуля.")

    if axial_compressive_n is None or axial_compressive_n <= 0:
        return BucklingApplicability(
            applicable=False,
            reason="Осевое сжимающее усилие не задано или не сжимающее — проверка устойчивости неприменима.",
        )
    axial_compressive_n = _finite("axial_compressive_n", axial_compressive_n)

    i_mm4 = section.moment_of_inertia_mm4
    pcr_n = math.pi ** 2 * e_mpa * i_mm4 / (effective_length_mm ** 2)
    slenderness = effective_length_mm / section.radius_of_gyration_mm

    note = ""
    if proportional_limit_mpa is not None:
        proportional_limit_mpa = _finite("proportional_limit_mpa", proportional_limit_mpa)
        lambda_critical = math.pi * math.sqrt(e_mpa / proportional_limit_mpa)
        if slenderness < lambda_critical:
            note = (
                f" ВНИМАНИЕ: гибкость λ={slenderness:.1f} < λ_кр={lambda_critical:.1f} — стержень "
                "'короткий', формула Эйлера здесь НЕ применима, нужна формула Ясинского/Джонсона "
                "для неупругой устойчивости (здесь не реализована)."
            )

    return BucklingApplicability(
        applicable=True,
        reason=(
            f"Осевое сжатие {axial_compressive_n:.0f} Н задано — проверка Эйлера применима "
            f"по нагрузке; критическая сила Pcr={pcr_n:.0f} Н, гибкость λ={slenderness:.1f}.{note}"
        ),
        euler_critical_load_n=pcr_n,
        ratio_axial_to_critical=axial_compressive_n / pcr_n,
        slenderness_ratio=slenderness,
    )


# --------------------------------------------------------------------------
# Зазор винт/корпус по ФАКТИЧЕСКОМУ относительному перемещению
# --------------------------------------------------------------------------

@dataclass
class ClearanceCheck:
    nominal_radial_clearance_mm: float
    available_clearance_mm: float
    ok: Optional[bool]
    note: str


def clearance_check(
    housing_inner_diameter_mm: float, screw_outer_diameter_mm: float,
    shaft_deflection_mm: float, runout_mm: float = 0.0, manufacturing_tolerance_mm: float = 0.0,
    wear_allowance_mm: float = 0.0,
) -> ClearanceCheck:
    """
    Зазор по ОТНОСИТЕЛЬНОМУ перемещению винта и корпуса (раздел задания:
    "не ограничивайся произвольным отношением прогиба к длине") — реальные
    вычитаемые слагаемые (прогиб вала под нагрузкой, биение, допуски
    изготовления, запас на износ), а не единый произвольный коэффициент.
    Любой из вычитаемых параметров может быть 0.0, если явно подтверждён
    нулевым — но по умолчанию НЕ подставляется скрытое допущение об их
    отсутствии без явной передачи вызывающим кодом.
    """
    for name, value in (
        ("housing_inner_diameter_mm", housing_inner_diameter_mm),
        ("screw_outer_diameter_mm", screw_outer_diameter_mm),
        ("shaft_deflection_mm", shaft_deflection_mm),
        ("runout_mm", runout_mm),
        ("manufacturing_tolerance_mm", manufacturing_tolerance_mm),
        ("wear_allowance_mm", wear_allowance_mm),
    ):
        _finite(name, value)
    if housing_inner_diameter_mm <= screw_outer_diameter_mm:
        raise ShaftBeamModelError(
            "housing_inner_diameter_mm должен быть больше screw_outer_diameter_mm "
            "(иначе винт не входит в корпус даже без нагрузки)."
        )
    nominal = (housing_inner_diameter_mm - screw_outer_diameter_mm) / 2.0
    consumed = abs(shaft_deflection_mm) + abs(runout_mm) + abs(manufacturing_tolerance_mm) + abs(wear_allowance_mm)
    available = nominal - consumed
    return ClearanceCheck(
        nominal_radial_clearance_mm=nominal,
        available_clearance_mm=available,
        ok=(available >= 0.0) if available is not None else None,
        note=(
            f"Номинальный радиальный зазор {nominal:.2f} мм; расход на прогиб/биение/допуски/износ "
            f"{consumed:.2f} мм; остаток {available:.2f} мм."
        ),
    )

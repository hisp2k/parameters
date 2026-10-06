# -*- coding: utf-8 -*-
"""
Исследовательский расчёт цепочки «вал → подшипники → корпус → рама →
основание» (Issue #3). Это ИССЛЕДОВАНИЕ, как и core/tube_shaft_study.py для
вала: результат НИКОГДА не попадает в release_gate (см. `StructuralChainResult.
is_research_only` и test_housing_frame_synthetic_example.py::
test_chain_result_never_claims_release_gate_relevance).

ИСТОРИЯ ИСПРАВЛЕНИЙ (для полного описания дефектов и почему они найдены —
см. calculator/TUBE_HOUSING_FRAME_STAGE_RU.md, там же — таблица «узел—режим
—усилие—результат—критерий—статус» актуального прогона):

- независимая проверка коммита 377e33c (P0.1/P0.2): корпус и рама собраны
  в ОДНУ FrameModel с общими узлами в точках крепления, заделка ТОЛЬКО в
  основании (устранена потерянная реакция H_MID, 10500 Н → 6400 Н);
  относительный зазор считается векторной разностью перемещений вала и
  корпуса (устранена подстановка 0.35 мм).
- независимая проверка коммита c24d42b (этот файл, раздел 2026-09-18):
  1. ЕДИНЫЙ источник геометрии сечения корпусной ТРУБЫ: раньше `housing_
     frame_section` (жёсткость для МКЭ) и `housing_frame_hollow_section`
     (геометрия для формул напряжений) были ДВУМЯ независимыми полями,
     которые можно было рассинхронизировать (repro: подменить только
     `housing_frame_hollow_section` — жёсткость останется прежней, а
     напряжение изменится в 1000 раз, функция не заметит противоречия), а
     диаметр расточки под зазор (`ClearanceInputs.housing_inner_diameter_mm`
     =140 мм) вообще не был связан с сечением трубы (`housing_frame_
     hollow_section`=Ø80/68 — труба Ø68 внутри физически НЕ вмещает вал
     Ø114, при этом использовалась именно как несущее сечение корпуса).
     Теперь `ChainGeometry.housing_tube_section` — ОДНО поле
     (`HollowCircularSection`), из которого ОДНОВременно выводятся
     жёсткость (A/Iy/Iz/J) для МКЭ, напряжения (bending/torsion) И
     внутренний диаметр для зазора (`ClearanceInputs` эти диаметры больше
     не хранит — они читаются из geometry). Разойтись эти три числа
     больше не могут — сомневаться не в чем, это один и тот же объект.
  2. Сечение РАМЫ (`ChainGeometry.frame_section`) отделено от сечения
     ТРУБЫ корпуса — это независимая несущая деталь (ноги/связи), не
     эквивалент трубы.
  3. Оси вала и расточки корпуса СОВМЕЩЕНЫ (`housing_drop_mm` убран —
     раньше 180 мм разноса осей ничем не было обосновано физически: вал
     проходит ВНУТРИ трубы корпуса, поэтому ось расточки подшипниковых
     гнёзд корпуса и ось вала — ОДНА линия, а не две параллельные).
     Кинематика ЖЁСТКОГО смещения точки, вынесенной из оси модели
     (u_точки = u_узла + θ×r, БЕЗ фиктивной сверхжёсткой связи) реализована
     как переиспользуемая утилита — `shaft_housing_clearance.
     rigid_offset_lateral_displacement()` — и используется, когда точка
     крепления РЕАЛЬНО не совпадает с осью элемента модели (см. её
     docstring и тесты); в ЭТОМ синтетическом примере она не нужна, так
     как ось расточки взята равной оси элемента модели.
  4. Проверка совместимости геометрии — несовместимые вход отвергаются:
     `housing_tube_section.inner_diameter_mm` обязан быть БОЛЬШЕ
     `shaft_section.outer_diameter_mm` (иначе вал физически не входит в
     трубу) — раньше это нигде не проверялось.
  5. Неизменяемый расчётный снимок и проверка ревизии/fingerprint НА
     ГРАНИЦЕ решателя (см. `frame_model.FrameModel.__post_init__`) —
     здесь используется автоматически (все узловые нагрузки этой цепочки
     строятся с одной и той же `loads.product_revision`/`input_
     fingerprint`). `StructuralChainResult.computed_fingerprint` (новое
     поле) зависит от ФАКТИЧЕСКИХ входов (геометрия+нагрузки+допуски
     зазора) через `compute_chain_fingerprint()` — смена любого входа
     меняет fingerprint (см. тесты).
  6. Подключён расчёт подшипников (`core/bearing_calculations.py`) к
     реакциям опор вала — Fr из двух поперечных компонент (вертикальная
     реакция + явный 0 по горизонтали — в этом примере нагрузка только
     вертикальная), Fa — целиком у ОСЕВО-ЗАФИКСИРОВАННОЙ опоры (см.
     `ShaftSupport.axially_fixed`), с СИНТЕТИЧЕСКИМИ каталожными входами
     (`BearingCatalogInputs`) — без каталожных данных статус опоры UNKNOWN,
     не блокируя остальной расчёт.
  7. Путь приводного момента показан явно и раздельно: момент передаётся
     ЧЕРЕЗ ВАЛ (`AppliedTorque` на входе/выходе вала, `torque_equilibrium_
     residual`==0) — радиальные подшипники в это НЕ вовлечены (Fr не
     содержит момента); РЕАКТИВНЫЙ момент корпуса мотор-редуктора передан
     ОТДЕЛЬНОЙ парой узловых моментов на корпус/раму (+T у выходного конца
     трубы — реакция стенки трубы на противомомент продукта, −T у
     крепления привода — реакция корпуса мотор-редуктора), сумма которых
     равна нулю (см. докстринг `calculate_structural_chain`, раздел
     «путь крутящего момента»).
  8. Путь осевой реакции: `AxialLoad` на валу, реакция целиком у
     осево-зафиксированной опоры — передана в корпус ТОЛЬКО в точке этой
     опоры (H_LOAD_A), у плавающей опоры (H_LOAD_B) осевая составляющая
     всегда 0 — выбор фиксирующей опоры буквально определяет путь.
  9. Внутренние силовые факторы (N/Qy/Qz/T/My/Mz) читаются для ВСЕХ 7
     элементов объединённой модели (`member_forces`), не только для
     одного консольного свеса — нормальное напряжение включает N/A ВМЕСТЕ
     с изгибом (консервативно, по модулю — см. `_combined_normal_stress_mpa`).
  10. Критическое сечение зазора ищется НЕПРЕРЫВНЫМ сканированием ВНУТРИ
      элементов корпуса (`frame_model.FrameSolution.
      transverse_displacement_along_member`, кубика Эрмита — точное
      решение для элемента без внутренней распределённой нагрузки), а не
      только по 5 узлам — узел является частным случаем сетки сканирования,
      а не единственным источником данных.
  11. Численная (не L/D-фильтр) оценка вклада сдвиговой деформации в
      прогиб вала — `shaft_beam_model.central_point_load_shear_deflection_
      estimate()`, отдельное число в результате и отчёте, не общий вывод
      "применимо/неприменимо".
  12. Независимая проверка равновесия ВСЕЙ цепочки, собранная из СЫРЫХ
      (не уже перенесённых в узлы FrameModel) реакций вала — см.
      `_raw_external_load_free_body_check`.

ЧЕСТНЫЕ ОГРАНИЧЕНИЯ (не скрыты — не путать с «готово»):
- геометрия/нагрузки/каталог подшипника — ПОЛНОСТЬЮ синтетические (см.
  `synthetic_example_geometry_and_loads()`), не TUBE-SAND-001;
- расчёт сварных/болтовых/анкерных соединений, местная прочность патрубков
  и плит — ВНЕ этого модуля (экспорт усилий сам по себе не закрывает
  прочность соединения — см. `unresolved_items`);
- усталость/устойчивость рамы, оценка сдвиговой податливости КОРПУСА
  (только вал численно оценён) — методика отсутствует;
- поиск критического сечения — сеткой конечного шага (не непрерывной
  оптимизацией) — см. `CLEARANCE_SCAN_POINTS_PER_MEMBER`.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import astuple, dataclass, is_dataclass
from typing import Optional

from calculator.core.bearing_calculations import (
    BearingCalculationError, BearingLifeOverflowError, dynamic_equivalent_load,
    l10_life_hours, resultant_radial_load_n, static_capacity_safety_factor,
)
from calculator.core.frame_model import (
    FrameMember, FrameModel, FrameNode, FrameSolution, NodalLoad, SectionProperties, Support,
)
from calculator.core.load_transfer import LoadCase, LoadCaseSet, LoadVector, Point3D
from calculator.core.shaft_beam_model import (
    PLANE_VERTICAL, AppliedTorque, AxialLoad, BeamLoadCase, BeamSolution, HollowCircularSection,
    PointLoad, ShaftSupport, ShearDeflectionEstimate, SteppedShaftProfile,
    bending_stress_mpa, central_point_load_shear_deflection_estimate, combined_von_mises_stress_mpa,
    solve_shear_moment, solve_deflection, torque_diagram, torque_equilibrium_residual,
    torsional_shear_stress_mpa,
)
from calculator.core.shaft_housing_clearance import (
    CriticalSectionClearanceResult, LateralDisplacement, SectionClearanceResult,
    critical_section_clearance, shaft_absolute_lateral_displacement_mm,
)

#: Число точек сканирования зазора на КАЖДЫЙ из 4 элементов корпуса (0 и 1 —
#: концы элемента включены) — раздел «P0/c24d42b, п.10»: критическое сечение
#: ищется сеткой ВНУТРИ элементов, а не только в узлах. Сетка конечного шага
#: — честно объявленное ограничение (не непрерывная оптимизация), см.
#: докстринг модуля.
CLEARANCE_SCAN_POINTS_PER_MEMBER = 21

#: Опора, воспринимающая ОСЕВОЕ усилие вала (см. ShaftSupport.axially_fixed)
#: — выбор фиксирующей опоры определяет путь осевой реакции (раздел задания).
FIXED_SUPPORT_LABEL = "опора_загрузки"
FLOATING_SUPPORT_LABEL = "опора_выгрузки"


class StructuralChainError(ValueError):
    pass


def _finite(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise StructuralChainError(f"{name}: ожидалось конечное число, получено {value!r}.")
    return float(value)


def _section_properties_from_hollow(hollow: HollowCircularSection, e_mpa: float, g_mpa: float) -> SectionProperties:
    """
    Единственное место, где жёсткость МКЭ (`SectionProperties`) строится
    ИЗ геометрии полого сечения — вызывается на КАЖДОМ обращении из
    ОДНОГО И ТОГО ЖЕ поля `ChainGeometry.housing_tube_section`, поэтому
    жёсткость и геометрия для формул напряжений/зазора не могут
    разойтись (независимая проверка c24d42b, раздел 1 докстринга модуля).
    """
    return SectionProperties(
        e_mpa=e_mpa, g_mpa=g_mpa, area_mm2=hollow.area_mm2,
        iy_mm4=hollow.moment_of_inertia_mm4, iz_mm4=hollow.moment_of_inertia_mm4,
        j_mm4=hollow.polar_moment_of_inertia_mm4, source=hollow.source,
    )


def _combined_normal_stress_mpa(axial_n: float, bending_moment_nmm: float, section: HollowCircularSection) -> float:
    """
    Нормальное напряжение = осевое (N/A) + изгибное (M/W) — независимая
    проверка c24d42b, раздел 9: "в нормальных напряжениях учитывай N/A
    вместе с изгибом". Совмещение — КОНСЕРВАТИВНО ПО МОДУЛЮ (наихудший
    случай — растяжение с той же стороны сечения, где максимален изгиб):
    `|N|/A + |M|/W`, а не векторное суммирование эпюр по толщине стенки
    (для этого нужно знать точную сторону сечения, где растяжение от N
    складывается с растяжением от M — вне точности этой модели, честно
    не скрыто).
    """
    return abs(axial_n) / section.area_mm2 + abs(bending_moment_nmm) / section.section_modulus_bending_mm3


@dataclass
class ChainGeometry:
    """Геометрия цепочки — ВСЕГДА явный вход, ничего не подставляется по умолчанию."""

    shaft_span_mm: float
    shaft_axis_z_mm: float
    housing_inset_mm: float         # смещение опор корпуса на раме внутрь от точек подшипников
    frame_leg_height_mm: float
    shaft_section: HollowCircularSection
    shaft_e_mpa: float
    shaft_g_mpa: float
    housing_tube_section: HollowCircularSection   # ЕДИНСТВЕННОЕ описание сечения ТРУБЫ корпуса — источник жёсткости+напряжений+диаметра зазора (см. докстринг модуля)
    housing_tube_e_mpa: float
    housing_tube_g_mpa: float
    frame_section: SectionProperties              # сечение НОГ/СВЯЗЕЙ рамы — НЕЗАВИСИМАЯ деталь от трубы корпуса


@dataclass
class ChainLoads:
    product_point_load_n: float     # вес винта+продукта, приложен в середине пролёта вала
    housing_self_weight_n: float    # собственный вес корпуса, приложен в H_MID
    drive_torque_nmm: float = 0.0   # приводной момент на входе вала (муфта мотор-редуктора)
    axial_force_n: float = 0.0      # осевое усилие вдоль вала (транспортирование продукта), знак — сжатие положительное (см. AxialLoad)
    product_revision: str = ""
    input_fingerprint: str = ""


@dataclass
class ClearanceInputs:
    """
    Диаметры бора/вала здесь БОЛЬШЕ НЕ хранятся (независимая проверка
    c24d42b, раздел 1) — читаются из `ChainGeometry.housing_tube_section`/
    `shaft_section`, чтобы не могли разойтись со стенкой, несущей нагрузку.
    """

    runout_mm: float = 0.0
    manufacturing_tolerance_mm: float = 0.0
    wear_allowance_mm: float = 0.0


@dataclass
class BearingCatalogInputs:
    """
    СИНТЕТИЧЕСКИЕ (НЕ подобранные под реальное изделие) каталожные входы
    для расчёта ОДНОГО типоразмера подшипника, применённого здесь к ОБЕИМ
    опорам вала (упрощение синтетического примера — честно названо, не
    скрытое допущение). Без этого объекта (`None`) расчёт подшипника для
    соответствующей опоры помечается `UNKNOWN`, но не останавливает
    остальную цепочку (раздел задания: "отсутствующие параметры оставляют
    конкретную проверку UNKNOWN/BLOCKED, но не останавливают доступные
    расчёты").
    """

    life_exponent: float           # LIFE_EXPONENT_BALL | LIFE_EXPONENT_ROLLER (bearing_calculations.py)
    dynamic_capacity_c_n: float
    static_capacity_c0_n: float
    x_factor: float
    y_factor: float
    x0_factor: float
    y0_factor: float
    rotation_speed_rpm: float
    bearing_type_label: str = "SYNTHETIC-catalog"
    source: str = "SYNTHETIC-catalog"


@dataclass
class BearingResult:
    support_label: str
    radial_load_n: float
    axial_load_n: float
    equivalent_dynamic_load_n: Optional[float]
    equivalent_static_load_n: Optional[float]
    l10_life_hours: Optional[float]
    static_safety_factor: Optional[float]
    status: str          # "РАСЧЁТНО" | "UNKNOWN" | "BLOCKED"
    note: str
    catalog_source: str = ""


def _calculate_bearing(
    support_label: str, radial_load_n: float, axial_load_n: float,
    catalog: Optional[BearingCatalogInputs],
) -> BearingResult:
    if catalog is None:
        return BearingResult(
            support_label=support_label, radial_load_n=radial_load_n, axial_load_n=axial_load_n,
            equivalent_dynamic_load_n=None, equivalent_static_load_n=None, l10_life_hours=None,
            static_safety_factor=None, status="UNKNOWN",
            note="Каталожные данные подшипника (C/C0/X/Y/частота) не переданы — расчёт этой "
                 "опоры не выполнен (не подставляется 'типичный' подшипник).",
        )
    dyn = dynamic_equivalent_load(radial_load_n, axial_load_n, catalog.x_factor, catalog.y_factor)
    stat = dynamic_equivalent_load(radial_load_n, axial_load_n, catalog.x0_factor, catalog.y0_factor)
    static_check = static_capacity_safety_factor(catalog.static_capacity_c0_n, stat.equivalent_load_n)
    try:
        life = l10_life_hours(
            catalog.dynamic_capacity_c_n, dyn.equivalent_load_n, catalog.rotation_speed_rpm,
            exponent=catalog.life_exponent,
        )
        life_hours = life.l10_life_hours
        status, note = "РАСЧЁТНО", f"ISO 281, {catalog.bearing_type_label}, каталог: {catalog.source} (СИНТЕТИЧЕСКИЙ)."
    except BearingLifeOverflowError as exc:
        life_hours = None
        status, note = "BLOCKED", f"L10h не представим при данных входах: {exc}"
    return BearingResult(
        support_label=support_label, radial_load_n=radial_load_n, axial_load_n=axial_load_n,
        equivalent_dynamic_load_n=dyn.equivalent_load_n, equivalent_static_load_n=stat.equivalent_load_n,
        l10_life_hours=life_hours, static_safety_factor=static_check.static_safety_factor,
        status=status, note=note, catalog_source=catalog.source,
    )


@dataclass
class AcceptanceRow:
    node: str
    mode: str
    load: str
    result: str
    criterion: str
    status: str
    affects_release_gate: bool = False   # ВСЕГДА False здесь — см. StructuralChainResult.is_research_only


@dataclass
class StructuralChainResult:
    geometry: ChainGeometry
    loads: ChainLoads
    shaft_solution: BeamSolution
    combined_model: FrameModel
    combined_solution: FrameSolution
    base_reaction_total_z_n: float
    external_applied_z_n: float
    equilibrium_residual: dict
    independent_free_body_residual: dict
    raw_external_load_free_body_residual: dict
    overhang_a_moment_nmm: float
    overhang_a_von_mises_mpa: float
    member_forces: dict            # member_id -> frame_model.MemberEndForces
    base_reactions: dict           # node_id -> dict(fx,fy,fz,mx,my,mz)
    bearing_results: dict          # support_label -> BearingResult
    shaft_von_mises_mpa: float
    shaft_shear_deflection_estimate: ShearDeflectionEstimate
    clearance: CriticalSectionClearanceResult
    computed_fingerprint: str
    acceptance_table: list  # list[AcceptanceRow]
    unresolved_items: list  # list[str]
    is_research_only: bool = True


def _stable_repr(value) -> str:
    if is_dataclass(value) and not isinstance(value, type):
        return repr(astuple(value))
    return repr(value)


def compute_chain_fingerprint(geometry: ChainGeometry, loads: ChainLoads, clearance_inputs: ClearanceInputs) -> str:
    """
    Fingerprint результата, зависящий от ФАКТИЧЕСКИХ входов (геометрия,
    материалы, опоры/связи через геометрию, нагрузки, допуски зазора) —
    независимая проверка c24d42b, раздел 2: "Fingerprint результата должен
    зависеть от фактических входов... изменение входов требует нового
    результата". Смена ЛЮБОГО числового поля geometry/loads/clearance_
    inputs меняет возвращаемую строку (см. тесты) — это НЕ криптографическая
    защита, только детерминированный отпечаток входов для трассируемости.
    """
    raw = "|".join([_stable_repr(geometry), _stable_repr(loads), _stable_repr(clearance_inputs)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _housing_member_and_local_s(x_mm: float, inset_mm: float, span_mm: float) -> tuple:
    """Отображает осевую координату x вдоль корпуса на (member_id, локальная s внутри элемента)."""
    if x_mm <= inset_mm:
        return "h_overhang_a", x_mm
    if x_mm <= span_mm / 2.0:
        return "h1", x_mm - inset_mm
    if x_mm <= span_mm - inset_mm:
        return "h2", x_mm - span_mm / 2.0
    return "h_overhang_b", x_mm - (span_mm - inset_mm)


def calculate_structural_chain(
    geometry: ChainGeometry, loads: ChainLoads, clearance_inputs: ClearanceInputs,
    bearing_catalog: Optional[BearingCatalogInputs] = None,
) -> StructuralChainResult:
    """
    Вызываемая функция приложения — собирает и решает ВСЮ цепочку
    вал→подшипники→корпус→рама→основание→зазор ОДНИМ вызовом, из явно
    переданных входов, ничего не подставляя молча.

    ПУТЬ КРУТЯЩЕГО МОМЕНТА (независимая проверка c24d42b, раздел «P1/п.7»).
    Момент передаётся ЧЕРЕЗ ВАЛ: `AppliedTorque(0, +T)` (вход муфты привода)
    и `AppliedTorque(span, −T)` (сопротивление продукта на выходе) —
    `torque_equilibrium_residual` этой пары равен 0 у вала САМОГО ПО СЕБЕ.
    РЕАКТИВНЫЙ момент передан в корпус/раму ОТДЕЛЬНОЙ, явно инженерно
    обоснованной парой моментов (а НЕ через радиальные подшипники — Fr
    берётся только из поперечных реакций, момент туда не входит):
      - `−T` в узле H_SUP_1 (крепление корпуса мотор-редуктора рядом со
        входом привода — противомомент, которым корпус редуктора реагирует
        на вращение своего выходного вала, Ньютон, 3-й закон);
      - `+T` в узле H_LOAD_B (стенка трубы корпуса реагирует на
        противомомент продукта у выходного конца — тот же продукт, что
        создаёт сопротивляющий момент `−T` на валу, своим противодействием
        нагружает СТЕНКУ ТРУБЫ, а не воздух).
    Сумма этих двух моментов на корпус/раму — РОВНО 0: реактивный момент
    замыкается ВНУТРИ корпуса/рамы (через h1/h2/brace_top), не "утекая" ни
    в основание, ни в никуда — раздел задания: "путь реактивного момента
    через корпус мотор-редуктора и его крепления", "отсутствие двойного
    счёта". Без этой пары момент продукта на выходном конце вала был бы
    внешним для системы (шаг+корпус+рама) БЕЗ видимой реакции — ровно тот
    же класс дефекта ("реакция исчезает"), что был найден и исправлен в
    P0.1 для средней опоры корпуса.

    ПУТЬ ОСЕВОЙ РЕАКЦИИ. `AxialLoad` на валу; вся осевая реакция — у
    ОСЕВО-ЗАФИКСИРОВАННОЙ опоры (`FIXED_SUPPORT_LABEL`, см. `ShaftSupport.
    axially_fixed`) — передаётся в корпус ТОЛЬКО в точке этой опоры
    (H_LOAD_A, `fx_n`); у плавающей опоры (H_LOAD_B) осевая составляющая
    нагрузки на корпус равна 0 буквально по построению (в `transferred_b`
    fx_n никогда не заполняется).
    """
    span = _finite("shaft_span_mm", geometry.shaft_span_mm)
    inset = _finite("housing_inset_mm", geometry.housing_inset_mm)
    leg_h = _finite("frame_leg_height_mm", geometry.frame_leg_height_mm)
    shaft_axis_z = _finite("shaft_axis_z_mm", geometry.shaft_axis_z_mm)
    if not (0.0 < inset < span / 2.0):
        raise StructuralChainError(
            f"housing_inset_mm={inset} должен быть в диапазоне (0, span/2={span / 2.0}) — "
            "иначе точки крепления корпуса к раме не образуют консольных свесов "
            "с обеих сторон (см. докстринг модуля)."
        )
    if geometry.housing_tube_section.inner_diameter_mm <= geometry.shaft_section.outer_diameter_mm:
        raise StructuralChainError(
            f"housing_tube_section.inner_diameter_mm={geometry.housing_tube_section.inner_diameter_mm} "
            f"должен быть БОЛЬШЕ shaft_section.outer_diameter_mm={geometry.shaft_section.outer_diameter_mm} "
            "— иначе вал физически не входит в трубу корпуса (независимая проверка c24d42b, "
            "раздел 1: несовместимая геометрия отвергается, а не тихо считается)."
        )

    drive_torque_nmm = _finite("drive_torque_nmm", loads.drive_torque_nmm)
    axial_force_n = _finite("axial_force_n", loads.axial_force_n)

    # --- 1. Вал: реакции опор, прогиб, момент/крутящий момент -----------
    p = _finite("product_point_load_n", loads.product_point_load_n)
    case = BeamLoadCase(
        total_length_mm=span,
        supports=[
            ShaftSupport(0.0, axially_fixed=True, label=FIXED_SUPPORT_LABEL),
            ShaftSupport(span, label=FLOATING_SUPPORT_LABEL),
        ],
        point_loads=[PointLoad(span / 2.0, p, PLANE_VERTICAL)],
        axial_loads=[AxialLoad(axial_force_n, label="осевое_усилие_продукта")] if axial_force_n else [],
    )
    shaft_solution = solve_shear_moment(case, PLANE_VERTICAL)
    shaft_solution = solve_deflection(
        shaft_solution, SteppedShaftProfile.uniform(span, geometry.shaft_section, geometry.shaft_e_mpa),
    )
    r_a = _finite("shaft_reaction_a_n", shaft_solution.reactions.support_a_n)
    r_b = _finite("shaft_reaction_b_n", shaft_solution.reactions.support_b_n)
    axial_reaction_on_shaft_n = (
        _finite("shaft_axial_reaction_n", shaft_solution.reactions.axial_support_n)
        if shaft_solution.reactions.axial_support_n is not None else 0.0
    )

    # Момент через вал: вход привода (+T) и сопротивление продукта (−T) —
    # см. докстринг выше. Единицы AppliedTorque — Н·м (torque_nm).
    torques = [
        AppliedTorque(0.0, drive_torque_nmm / 1000.0, label="вход_привода"),
        AppliedTorque(span, -drive_torque_nmm / 1000.0, label="сопротивление_продукта"),
    ]
    shaft_torque_residual = torque_equilibrium_residual(torques)
    shaft_torque_at_midspan_nmm = torque_diagram(torques, span / 2.0) * 1000.0

    # Собственная прочность вала (изгиб midspan + кручение) — момент через
    # ВАЛ, не через подшипники (раздел «путь момента» докстринга модуля).
    shaft_bending_moment_nmm = shaft_solution.moment(span / 2.0)
    shaft_bending_stress_mpa = bending_stress_mpa(shaft_bending_moment_nmm, geometry.shaft_section)
    shaft_torsion_stress_mpa = torsional_shear_stress_mpa(shaft_torque_at_midspan_nmm, geometry.shaft_section)
    shaft_von_mises = combined_von_mises_stress_mpa(shaft_bending_stress_mpa, shaft_torsion_stress_mpa)

    shaft_shear_estimate = central_point_load_shear_deflection_estimate(
        span, p, geometry.shaft_section, geometry.shaft_e_mpa, geometry.shaft_g_mpa,
    )

    # --- 2. Перенос реакций подшипников в точки крепления корпуса ------
    # Оси вала и расточки корпуса СОВМЕЩЕНЫ (см. докстринг модуля, п.3) —
    # точка крепления корпуса РАВНА точке опоры вала, перенос НЕ добавляет
    # искусственного плеча (r=0 при transferred_to этой же точки).
    point_support_a_shaft = Point3D(0.0, 0.0, shaft_axis_z)
    point_support_b_shaft = Point3D(span, 0.0, shaft_axis_z)
    point_mount_a = point_support_a_shaft
    point_mount_b = point_support_b_shaft

    transfer_set = LoadCaseSet()
    transfer_set.add(LoadVector(
        node_ref=FIXED_SUPPORT_LABEL, point=point_support_a_shaft,
        fx_n=-axial_reaction_on_shaft_n, fy_n=0.0, fz_n=-r_a,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING,
        source="shaft_beam_model.solve_reactions#support_a", label="реакция_на_корпус_A",
        product_revision=loads.product_revision, input_fingerprint=loads.input_fingerprint,
    ))
    transfer_set.add(LoadVector(
        node_ref=FLOATING_SUPPORT_LABEL, point=point_support_b_shaft, fx_n=0.0, fy_n=0.0, fz_n=-r_b,
        mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0, load_case=LoadCase.OPERATING,
        source="shaft_beam_model.solve_reactions#support_b", label="реакция_на_корпус_B",
        product_revision=loads.product_revision, input_fingerprint=loads.input_fingerprint,
    ))
    transferred_a = transfer_set.loads[0].transferred_to(point_mount_a)
    transferred_b = transfer_set.loads[1].transferred_to(point_mount_b)

    # --- 2b. Подшипники — Fr из двух поперечных компонент, Fa у фиксирующей опоры ---
    fr_a = resultant_radial_load_n(r_a, 0.0)   # 0.0 — явная горизонтальная составляющая: в этом примере не нагружена
    fr_b = resultant_radial_load_n(r_b, 0.0)
    bearing_results = {
        FIXED_SUPPORT_LABEL: _calculate_bearing(FIXED_SUPPORT_LABEL, fr_a, abs(axial_reaction_on_shaft_n), bearing_catalog),
        FLOATING_SUPPORT_LABEL: _calculate_bearing(FLOATING_SUPPORT_LABEL, fr_b, 0.0, bearing_catalog),
    }

    # --- 3+4. Корпус и рама — ОДНА объединённая модель ------------------
    housing_z = shaft_axis_z
    point_sup_1 = Point3D(inset, 0.0, housing_z)
    point_mid = Point3D(span / 2.0, 0.0, housing_z)
    point_sup_2 = Point3D(span - inset, 0.0, housing_z)
    base_1 = Point3D(point_sup_1.x_mm, point_sup_1.y_mm, point_sup_1.z_mm - leg_h)
    base_2 = Point3D(point_sup_2.x_mm, point_sup_2.y_mm, point_sup_2.z_mm - leg_h)

    housing_section = _section_properties_from_hollow(
        geometry.housing_tube_section, geometry.housing_tube_e_mpa, geometry.housing_tube_g_mpa,
    )
    frame_section = geometry.frame_section
    nodes = [
        FrameNode("H_LOAD_A", point_mount_a), FrameNode("H_SUP_1", point_sup_1),
        FrameNode("H_MID", point_mid), FrameNode("H_SUP_2", point_sup_2),
        FrameNode("H_LOAD_B", point_mount_b),
        FrameNode("F_BASE_1", base_1), FrameNode("F_BASE_2", base_2),
    ]
    members = [
        FrameMember("h_overhang_a", "H_LOAD_A", "H_SUP_1", housing_section),
        FrameMember("h1", "H_SUP_1", "H_MID", housing_section),
        FrameMember("h2", "H_MID", "H_SUP_2", housing_section),
        FrameMember("h_overhang_b", "H_SUP_2", "H_LOAD_B", housing_section),
        FrameMember("leg_1", "F_BASE_1", "H_SUP_1", frame_section),
        FrameMember("leg_2", "F_BASE_2", "H_SUP_2", frame_section),
        FrameMember("brace_top", "H_SUP_1", "H_SUP_2", frame_section),
    ]
    # ЕДИНСТВЕННЫЕ опоры всей объединённой цепочки — заделка в основании.
    supports = [Support.fixed("F_BASE_1"), Support.fixed("F_BASE_2")]
    combined_loads = [
        NodalLoad.from_load_vector("H_LOAD_A", transferred_a, expected_point=point_mount_a),
        NodalLoad.from_load_vector("H_LOAD_B", transferred_b, expected_point=point_mount_b),
        NodalLoad(
            "H_MID", fz_n=-loads.housing_self_weight_n, label="собственный_вес_корпуса",
            source="synthetic-example#housing_self_weight", load_cases=(LoadCase.SELF_WEIGHT,),
            product_revision=loads.product_revision, input_fingerprint=loads.input_fingerprint,
        ),
    ]
    if drive_torque_nmm:
        combined_loads.append(NodalLoad(
            "H_SUP_1", mx_nmm=-drive_torque_nmm, label="реакция_момента_привода_на_раму",
            source="synthetic-example#motor_reducer_reaction_torque", load_cases=(LoadCase.OPERATING,),
            product_revision=loads.product_revision, input_fingerprint=loads.input_fingerprint,
        ))
        combined_loads.append(NodalLoad(
            "H_LOAD_B", mx_nmm=drive_torque_nmm, label="реакция_стенки_на_противомомент_продукта",
            source="synthetic-example#product_counter_torque_reaction", load_cases=(LoadCase.OPERATING,),
            product_revision=loads.product_revision, input_fingerprint=loads.input_fingerprint,
        ))
    combined_model = FrameModel(nodes, members, supports, loads=combined_loads)
    combined_solution = combined_model.solve()

    equilibrium_residual = combined_solution.equilibrium_residual()
    independent_free_body_residual = combined_solution.independent_free_body_check(Point3D(0.0, 0.0, 0.0))

    base_reaction_total_z = (
        combined_solution.reaction_at("F_BASE_1", "uz") + combined_solution.reaction_at("F_BASE_2", "uz")
    )
    external_applied_z = transferred_a.fz_n + transferred_b.fz_n - loads.housing_self_weight_n

    # --- Внутренние силовые факторы N/Qy/Qz/T/My/Mz для ВСЕХ элементов ---
    member_forces = {m.member_id: combined_solution.member_end_forces(m.member_id) for m in members}
    # reaction_at ожидает имена DOF модели (ux..rz), а не fx..mz — переводим явно.
    _dof_to_reaction_name = {"fx": "ux", "fy": "uy", "fz": "uz", "mx": "rx", "my": "ry", "mz": "rz"}
    base_reactions = {
        node_id: {key: combined_solution.reaction_at(node_id, dof) for key, dof in _dof_to_reaction_name.items()}
        for node_id in ("F_BASE_1", "F_BASE_2")
    }

    end_forces_overhang_a = member_forces["h_overhang_a"]
    m_res_nmm = math.hypot(end_forces_overhang_a.my_j, end_forces_overhang_a.mz_j)
    t_res_nmm = end_forces_overhang_a.t_j
    housing_hollow_section = geometry.housing_tube_section
    sigma = _combined_normal_stress_mpa(end_forces_overhang_a.n_j, m_res_nmm, housing_hollow_section)
    tau = torsional_shear_stress_mpa(t_res_nmm, housing_hollow_section)
    mises = combined_von_mises_stress_mpa(sigma, tau)

    # --- 5. Относительный зазор вал/корпус — сканирование ВНУТРИ элементов ---
    support_a_absolute = LateralDisplacement(
        dy_mm=0.0, dz_mm=combined_solution.displacement_at("H_LOAD_A", "uz"),
    )
    support_b_absolute = LateralDisplacement(
        dy_mm=0.0, dz_mm=combined_solution.displacement_at("H_LOAD_B", "uz"),
    )
    sections = []
    candidate_labels = {0.0: "H_LOAD_A", inset: "H_SUP_1", span / 2.0: "H_MID", span - inset: "H_SUP_2", span: "H_LOAD_B"}
    boundaries = [0.0, inset, span / 2.0, span - inset, span]
    xs = set()
    for lo, hi in zip(boundaries[:-1], boundaries[1:]):
        for k in range(CLEARANCE_SCAN_POINTS_PER_MEMBER):
            xs.add(lo + (hi - lo) * k / (CLEARANCE_SCAN_POINTS_PER_MEMBER - 1))
    for x_mm in sorted(xs):
        member_id, s_mm = _housing_member_and_local_s(x_mm, inset, span)
        relative_dz = shaft_solution.deflection_mm(x_mm)
        shaft_abs = shaft_absolute_lateral_displacement_mm(
            x_mm, 0.0, support_a_absolute, span, support_b_absolute,
            relative_dy_mm=0.0, relative_dz_mm=relative_dz,
        )
        _gx, gy, gz = combined_solution.transverse_displacement_along_member(member_id, s_mm)
        housing_abs = LateralDisplacement(dy_mm=gy, dz_mm=gz)
        consumed = math.hypot(shaft_abs.dy_mm - housing_abs.dy_mm, shaft_abs.dz_mm - housing_abs.dz_mm)
        label = candidate_labels.get(x_mm, f"{member_id}@{s_mm:.1f}мм")
        sections.append(SectionClearanceResult(
            x_mm=x_mm, shaft_absolute=shaft_abs, housing_absolute=housing_abs,
            consumed_by_deflection_mm=consumed, label=label,
        ))
    clearance_result = critical_section_clearance(
        sections,
        housing_inner_diameter_mm=geometry.housing_tube_section.inner_diameter_mm,
        screw_outer_diameter_mm=geometry.shaft_section.outer_diameter_mm,
        runout_mm=clearance_inputs.runout_mm,
        manufacturing_tolerance_mm=clearance_inputs.manufacturing_tolerance_mm,
        wear_allowance_mm=clearance_inputs.wear_allowance_mm,
    )

    # --- Независимая проверка равновесия ВСЕЙ цепочки из СЫРЫХ нагрузок ---
    raw_residual = _raw_external_load_free_body_check(
        point_support_a_shaft=point_support_a_shaft, r_a=r_a,
        point_support_b_shaft=point_support_b_shaft, r_b=r_b,
        axial_reaction_on_shaft_n=axial_reaction_on_shaft_n,
        point_mid=point_mid, housing_self_weight_n=loads.housing_self_weight_n,
        point_sup_1=point_sup_1, point_load_b=point_mount_b, drive_torque_nmm=drive_torque_nmm,
        combined_solution=combined_solution, reference_point=Point3D(0.0, 0.0, 0.0),
    )

    computed_fingerprint = compute_chain_fingerprint(geometry, loads, clearance_inputs)

    # --- Таблица «узел—режим—нагрузка—результат—критерий—статус» -------
    shaft_equilibrium_ok = abs((r_a + r_b) - p) < 1e-6
    base_equilibrium_ok = abs(base_reaction_total_z + external_applied_z) < 1e-6
    free_body_ok = all(abs(v) < 1e-6 for v in independent_free_body_residual.values())
    raw_free_body_ok = all(abs(v) < 1e-6 for v in raw_residual.values())
    torque_path_ok = abs(shaft_torque_residual) < 1e-9

    acceptance_table = [
        AcceptanceRow(
            node="вал (обе опоры)", mode=LoadCase.OPERATING.value,
            load=f"P={p:.1f} Н в середине пролёта",
            result=f"r_a+r_b={r_a + r_b:.1f} Н",
            criterion=f"= приложенной нагрузке ({p:.1f} Н)",
            status="OK" if shaft_equilibrium_ok else "FAIL",
        ),
        AcceptanceRow(
            node="вал — момент через ВАЛ (не подшипники)", mode=LoadCase.OPERATING.value,
            load=f"T={drive_torque_nmm / 1000.0:.1f} Н·м вход / −{drive_torque_nmm / 1000.0:.1f} Н·м выход",
            result=f"невязка момента вала: {shaft_torque_residual:.6e} Н·м, "
                   f"σ_экв(изгиб+кручение, midspan)={shaft_von_mises:.2f} МПа",
            criterion="невязка ≈0; критерий прочности НЕ применён (нет допускаемого напряжения материала вала)",
            status="OK" if torque_path_ok else "FAIL",
        ),
        AcceptanceRow(
            node="корпус+рама (единая модель)", mode=LoadCase.OPERATING.value,
            load="реакции вала (перенесены, вкл. осевую) + вес корпуса + реактивный момент привода",
            result=f"невязка K·u: {max(abs(v) for v in equilibrium_residual.values()):.3e}",
            criterion="≈0 (равновесие всей объединённой модели)",
            status="OK" if all(abs(v) < 1e-6 for v in equilibrium_residual.values()) else "FAIL",
        ),
        AcceptanceRow(
            node="вся цепочка (свободное тело, нагрузки FrameModel)", mode=LoadCase.OPERATING.value,
            load="внешние нагрузки + реакции основания",
            result=f"невязка (независимая проверка): {max(abs(v) for v in independent_free_body_residual.values()):.3e}",
            criterion="≈0 по 3 силам и 3 моментам относительно начала координат",
            status="OK" if free_body_ok else "FAIL",
        ),
        AcceptanceRow(
            node="вся цепочка (свободное тело, СЫРЫЕ исходные нагрузки)", mode=LoadCase.OPERATING.value,
            load="СЫРЫЕ реакции вала (до переноса) + вес + реактивный момент + реакции основания",
            result=f"невязка (независимо от combined_loads): {max(abs(v) for v in raw_residual.values()):.3e}",
            criterion="≈0 — независимо построено из исходных физических величин, "
                      "не переиспользует combined_loads/transfer_set",
            status="OK" if raw_free_body_ok else "FAIL",
        ),
        AcceptanceRow(
            node="основание (F_BASE_1+F_BASE_2)", mode=LoadCase.OPERATING.value,
            load=f"суммарная внешняя нагрузка на цепочку {external_applied_z:.1f} Н (знак: вниз отрицательно)",
            result=f"ΣR_z={base_reaction_total_z:.1f} Н",
            criterion=f"ΣR_z + F_внешняя ≈ 0 → |ΣR_z| = {abs(external_applied_z):.1f} Н",
            status="OK" if base_equilibrium_ok else "FAIL",
        ),
        AcceptanceRow(
            node="консольный свес корпуса (h_overhang_a)", mode=LoadCase.OPERATING.value,
            load=f"реакция вала (радиальная+осевая), перенесённая на плечо {inset:.1f} мм",
            result=f"σ_экв={mises:.2f} МПа (N={end_forces_overhang_a.n_j:.0f} Н, "
                   f"M={m_res_nmm:.0f} Н·мм, T={t_res_nmm:.0f} Н·мм)",
            criterion="ИССЛЕДОВАТЕЛЬСКИЙ результат — критерий прочности НЕ применён; расчёт "
                      "местных соединений (сварка/болты/анкера) — ВНЕ этого модуля",
            status="РАСЧЁТНО" if math.isfinite(mises) else "FAIL",
        ),
    ]
    for label, result in bearing_results.items():
        if result.status == "UNKNOWN":
            row_result = "нет каталожных данных"
        elif result.status == "BLOCKED":
            row_result = result.note
        else:
            row_result = (
                f"Fr={result.radial_load_n:.0f} Н, Fa={result.axial_load_n:.0f} Н, "
                f"P={result.equivalent_dynamic_load_n:.0f} Н, "
                f"L10h={result.l10_life_hours:,.0f} ч, s0={result.static_safety_factor:.2f}"
            )
        acceptance_table.append(AcceptanceRow(
            node=f"подшипник {label}", mode=LoadCase.OPERATING.value,
            load=f"Fr/Fa из реакций вала (фиксирующая опора: {FIXED_SUPPORT_LABEL})",
            result=row_result,
            criterion="ИССЛЕДОВАТЕЛЬСКИЙ результат — минимально требуемые L10h/s0 НЕ заданы заказчиком",
            status=result.status,
        ))
    acceptance_table.append(AcceptanceRow(
        node=f"зазор вал/корпус, критическое сечение={clearance_result.governing_section.label}",
        mode=LoadCase.OPERATING.value,
        load="совместный прогиб вала и корпуса (векторная разность, сканирование внутри элементов)",
        result=f"расход зазора={clearance_result.governing_section.consumed_by_deflection_mm:.3f} мм, "
               f"остаток={clearance_result.clearance.available_clearance_mm:.3f} мм "
               f"(проверено {len(sections)} сечений)",
        criterion="остаток зазора > 0",
        status="OK" if clearance_result.clearance.ok else "FAIL",
    ))
    acceptance_table.append(AcceptanceRow(
        node="вал — сдвиговая податливость (численная оценка)", mode=LoadCase.OPERATING.value,
        load=f"P={p:.1f} Н в середине пролёта (та же схема, что и прогиб)",
        result=f"δ_сдвиг/δ_изгиб={shaft_shear_estimate.shear_to_bending_ratio * 100.0:.2f}%",
        criterion="ИССЛЕДОВАТЕЛЬСКИЙ результат — численная оценка, не бинарный L/D-фильтр; "
                  "порог значимости заказчиком не задан",
        status="РАСЧЁТНО",
    ))

    unresolved_items = [
        "Реальная геометрия/BOM корпуса и рамы TUBE-SAND-001 (владелец: CAD/конструктор) — "
        "calculator/data/TUBE-SAND-001.json на момент этого расчёта ОТСУТСТВУЕТ как в git, "
        "так и в рабочем дереве на рабочей станции (проверено ОДИН раз через файловый мост "
        "к рабочей станции, см. TUBE_HOUSING_FRAME_STAGE_RU.md, раздел «Проверка CAD/моста»); "
        "мост ClaudeBridge технически присутствует в репозитории, но последний зафиксированный "
        "вызов через него (calculator/../ClaudeBridge/request.json) не относится к TUBE-SAND-001 "
        "и не выполнялся в рамках этого расчёта — активный запрос к CAD не отправлялся.",
        "Реальные расчётные случаи нагружения и коэффициенты подтверждённой перегрузки/"
        "заклинивания (владелец: технолог/заказчик) — использован ТОЛЬКО режим "
        "'рабочий_режим', остальные LoadCase (пуск, расчётное заполнение, транспортировка) "
        "не считаны в этом исследовании.",
        "Реальные каталожные C/C0/X/Y/X0/Y0 и посадки подшипников (владелец: каталог привода/"
        "подшипников) — если bearing_catalog не передан, соответствующая строка помечена "
        "UNKNOWN; в синтетическом примере передан ПОЛНОСТЬЮ синтетический каталог (не "
        "привязан ни к одному реальному типоразмеру).",
        "Расчёт сварных/болтовых/анкерных соединений и локальных концентраторов напряжений "
        "в узлах крепления (патрубки/плиты/анкера) — ВНЕ этого модуля; экспорт внутренних "
        "усилий (member_forces/base_reactions) сам по себе НЕ закрывает прочность соединения.",
        "Усталость (циклическая прочность) и устойчивость рамы — методика отсутствует "
        "(см. TUBE_SHAFT_STRENGTH_STAGE_RU.md, раздел 3).",
        "Сдвиговая податливость КОРПУСА/РАМЫ (в отличие от вала) — численно не оценена; "
        "FrameModel по-прежнему чистый Эйлер–Бернулли без сдвиговой поправки "
        "(см. FrameModel.known_limitations()) — применимость для корпуса/рамы НЕ проверена.",
        "Поиск критического сечения зазора — сеткой конечного шага "
        f"({CLEARANCE_SCAN_POINTS_PER_MEMBER} точек на элемент), не непрерывной оптимизацией — "
        "сходимость шага сетки отдельно не исследована.",
        "Кинематика жёсткого смещения точки крепления, вынесенной из оси модели "
        "(rigid_offset_lateral_displacement) — реализована и протестирована как утилита, но "
        "НЕ используется в этом синтетическом примере (оси вала и расточки корпуса здесь "
        "совмещены намеренно) — для реального изделия с реальным смещением осей это отдельный вход.",
    ]

    return StructuralChainResult(
        geometry=geometry, loads=loads, shaft_solution=shaft_solution,
        combined_model=combined_model, combined_solution=combined_solution,
        base_reaction_total_z_n=base_reaction_total_z, external_applied_z_n=external_applied_z,
        equilibrium_residual=equilibrium_residual,
        independent_free_body_residual=independent_free_body_residual,
        raw_external_load_free_body_residual=raw_residual,
        overhang_a_moment_nmm=m_res_nmm, overhang_a_von_mises_mpa=mises,
        member_forces=member_forces, base_reactions=base_reactions, bearing_results=bearing_results,
        shaft_von_mises_mpa=shaft_von_mises, shaft_shear_deflection_estimate=shaft_shear_estimate,
        clearance=clearance_result, computed_fingerprint=computed_fingerprint,
        acceptance_table=acceptance_table,
        unresolved_items=unresolved_items, is_research_only=True,
    )


def _raw_external_load_free_body_check(
    *, point_support_a_shaft: Point3D, r_a: float, point_support_b_shaft: Point3D, r_b: float,
    axial_reaction_on_shaft_n: float, point_mid: Point3D, housing_self_weight_n: float,
    point_sup_1: Point3D, point_load_b: Point3D, drive_torque_nmm: float,
    combined_solution: FrameSolution, reference_point: Point3D,
) -> dict:
    """
    Независимая проверка равновесия ВСЕЙ цепочки (независимая проверка
    c24d42b, раздел «результат и приёмка»: "используй исходные внешние
    нагрузки, а не только уже перенесённые нагрузки FrameModel; внутренние
    реакции исключи"). В отличие от `FrameSolution.independent_free_body_
    check()` (которая суммирует `self.model.loads` — то есть УЖЕ
    построенные `combined_loads`, прошедшие через `transfer_set`/
    `NodalLoad.from_load_vector`), здесь нагрузки строятся ЗАНОВО из
    СЫРЫХ физических величин (`r_a`, `r_b`, осевая реакция, вес, момент) —
    ни один объект отсюда не переиспользуется из `calculate_structural_
    chain()`. Совпадение результата с `independent_free_body_check()`
    было бы недостаточно строгим тестом (обе проверки использовали бы
    ОДНИ И ТЕ ЖЕ вычисленные значения `combined_loads>`) — здесь путь
    независим НАЧИНАЯ С физических входных чисел, а не только с точки
    сложения.
    """
    vectors = [
        LoadVector(
            node_ref="опора_загрузки_сырое", point=point_support_a_shaft,
            fx_n=-axial_reaction_on_shaft_n, fy_n=0.0, fz_n=-r_a, mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0,
            load_case=LoadCase.OPERATING, source="housing_frame_study._raw_external_load_free_body_check#shaft_a",
        ),
        LoadVector(
            node_ref="опора_выгрузки_сырое", point=point_support_b_shaft,
            fx_n=0.0, fy_n=0.0, fz_n=-r_b, mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0,
            load_case=LoadCase.OPERATING, source="housing_frame_study._raw_external_load_free_body_check#shaft_b",
        ),
        LoadVector(
            node_ref="корпус_сырое", point=point_mid,
            fx_n=0.0, fy_n=0.0, fz_n=-housing_self_weight_n, mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0,
            load_case=LoadCase.SELF_WEIGHT, source="housing_frame_study._raw_external_load_free_body_check#housing_weight",
        ),
    ]
    if drive_torque_nmm:
        vectors.append(LoadVector(
            node_ref="привод_сырое", point=point_sup_1,
            fx_n=0.0, fy_n=0.0, fz_n=0.0, mx_nmm=-drive_torque_nmm, my_nmm=0.0, mz_nmm=0.0,
            load_case=LoadCase.OPERATING, source="housing_frame_study._raw_external_load_free_body_check#motor_reaction",
        ))
        vectors.append(LoadVector(
            node_ref="продукт_противомомент_сырое", point=point_load_b,
            fx_n=0.0, fy_n=0.0, fz_n=0.0, mx_nmm=drive_torque_nmm, my_nmm=0.0, mz_nmm=0.0,
            load_case=LoadCase.OPERATING, source="housing_frame_study._raw_external_load_free_body_check#product_reaction",
        ))
    for base_node in ("F_BASE_1", "F_BASE_2"):
        node = combined_solution.model.node(base_node)
        vectors.append(LoadVector(
            node_ref=f"{base_node}_сырое", point=node.point,
            fx_n=combined_solution.reaction_at(base_node, "ux"),
            fy_n=combined_solution.reaction_at(base_node, "uy"),
            fz_n=combined_solution.reaction_at(base_node, "uz"),
            mx_nmm=combined_solution.reaction_at(base_node, "rx"),
            my_nmm=combined_solution.reaction_at(base_node, "ry"),
            mz_nmm=combined_solution.reaction_at(base_node, "rz"),
            load_case=LoadCase.OPERATING,
            source="housing_frame_study._raw_external_load_free_body_check#base_reaction",
        ))

    fx = fy = fz = mx = my = mz = 0.0
    for v in vectors:
        t = v.transferred_to(reference_point)
        fx += t.fx_n; fy += t.fy_n; fz += t.fz_n
        mx += t.mx_nmm; my += t.my_nmm; mz += t.mz_nmm
    return {"fx": fx, "fy": fy, "fz": fz, "mx": mx, "my": my, "mz": mz}


# ---------------------------------------------------------------------------
# Синтетический пример (НЕ TUBE-SAND-001, см. общий докстринг модуля и
# tests/test_housing_frame_synthetic_example.py) — вынесен сюда, чтобы тест
# вызывал ГОТОВУЮ функцию приложения, а не собирал схему заново.
# ---------------------------------------------------------------------------

def synthetic_example_geometry_and_loads() -> tuple:
    """
    Возвращает (ChainGeometry, ChainLoads, ClearanceInputs, BearingCatalogInputs)
    для полностью синтетического примера — числа НАРОЧИТО отличаются от
    исследовательских величин TUBE-SAND-001 (2515 мм, 35° и т.п., см.
    core/tube_shaft_study.py), чтобы результат нельзя было спутать с
    реальным изделием.

    ФИЗИЧЕСКАЯ СОГЛАСОВАННОСТЬ (независимая проверка c24d42b, раздел 1):
    вал Ø114/94 мм; труба корпуса Ø168/140 мм (внутренний диаметр 140 мм
    БОЛЬШЕ наружного диаметра вала 114 мм — вал физически входит в трубу,
    номинальный радиальный зазор (140−114)/2=13 мм); сечение рамы (ноги/
    связи) — ОТДЕЛЬНАЯ деталь Ø120/100 мм, не эквивалент трубы корпуса;
    оси вала и расточки корпуса СОВМЕЩЕНЫ (housing_drop_mm убран).
    """
    shaft_section = HollowCircularSection(outer_diameter_mm=114.0, inner_diameter_mm=94.0, source="synthetic-example")
    housing_tube_section = HollowCircularSection(outer_diameter_mm=168.0, inner_diameter_mm=140.0, source="synthetic-example")
    frame_section_hollow = HollowCircularSection(outer_diameter_mm=120.0, inner_diameter_mm=100.0, source="synthetic-example")
    frame_section = _section_properties_from_hollow(frame_section_hollow, e_mpa=200000.0, g_mpa=77000.0)
    geometry = ChainGeometry(
        shaft_span_mm=1800.0, shaft_axis_z_mm=500.0, housing_inset_mm=300.0,
        frame_leg_height_mm=900.0, shaft_section=shaft_section, shaft_e_mpa=210000.0, shaft_g_mpa=80000.0,
        housing_tube_section=housing_tube_section, housing_tube_e_mpa=200000.0, housing_tube_g_mpa=77000.0,
        frame_section=frame_section,
    )
    loads = ChainLoads(
        product_point_load_n=6000.0, housing_self_weight_n=400.0,
        drive_torque_nmm=2.0e6, axial_force_n=1500.0,
        product_revision="synthetic-example-rev1", input_fingerprint="synthetic-example-fp1",
    )
    clearance_inputs = ClearanceInputs(runout_mm=0.2, manufacturing_tolerance_mm=0.15, wear_allowance_mm=0.5)
    bearing_catalog = BearingCatalogInputs(
        life_exponent=3.0, dynamic_capacity_c_n=60000.0, static_capacity_c0_n=50000.0,
        x_factor=1.0, y_factor=0.5, x0_factor=1.0, y0_factor=0.5, rotation_speed_rpm=45.0,
        bearing_type_label="шариковый радиальный (СИНТЕТИЧЕСКИЙ типоразмер)",
        source="SYNTHETIC-catalog, не привязан к реальному изделию",
    )
    return geometry, loads, clearance_inputs, bearing_catalog

# -*- coding: utf-8 -*-
"""
Инженерное ядро для валового ТРУБЧАТОГО шнекового транспортёра
(ConveyorKind.SHAFTED_TUBE = "валовый_трубчатый") — GitHub Issue #3.

СОЗНАТЕЛЬНО ОТДЕЛЬНАЯ методика от core/screw_engineering.py (желобчатый
шнек), по прямому указанию задания ("Не использовать методику желобчатого
шнека для угла 35°"):

- `incline_correction_c()` того модуля жёстко ограничен 20° и подобран для
  ЖЕЛОБЧАТОЙ геометрии; коэффициенты FILL_FACTOR_PSI / STEP_TO_DIAMETER_RATIO /
  RESISTANCE_OMEGA / MAX_SPEED_A там же подобраны для желоба, а не для трубы.
  Этот модуль ничего из screw_engineering.py не импортирует и не переиспользует.
- Для трубного шнека на угол ~35° в этом репозитории НЕТ подтверждённой
  инженерной методики (в отличие от желобчатого — там был перенесённый
  черновик Stage 12 с указанными источниками). Никто такую методику для
  трубного шнека сюда не передавал.

Поэтому ядро честно делает ровно то, что можно сделать БЕЗ выдуманной
методики и без выдуманных свойств материала:

1. Перекрёстно проверяет ЧИСТУЮ ГЕОМЕТРИЮ (не инженерный расчёт, а
   тригонометрия): угол наклона (п.2 эскиза) против заявленных высот пола
   загрузки/выгрузки (п.6-7 эскиза) — см. `check_geometry_conflict()`.
2. Переводит производительность в т/ч, если это возможно без плотности
   (т/ч, кг/ч) или с уже известной плотностью (м3/ч) — это перевод единиц,
   не инженерная методика.
3. Для всего остального (диаметр корпуса, частота вращения, мощность,
   достижимая производительность) возвращает `TubeCalcStatus.BLOCKED` и
   точный список блокеров — вместо того, чтобы подставить желобчатую
   методику или выдуманные свойства материала (прямо запрещено заданием:
   "Не подставлять неизвестные свойства песка/смеси самостоятельно").

DN100 (присоединительный диаметр патрубка, п.1 эскиза) — задание прямо
требует не путать его с диаметром КОРПУСА трубного шнека. Здесь он хранится
отдельно (`connection_diameter_mm`) и НИКОГДА не копируется в `diameter_mm`
(диаметр корпуса) ни автоматически, ни по умолчанию.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TubeCalcStatus(str, Enum):
    BLOCKED = "заблокировано"            # инженерная часть не завершена — не хватает методики и/или данных
    GEOMETRY_ONLY = "только_геометрия"   # зарезервировано на будущее, если геометрия станет единственным блокером
    COMPUTED = "рассчитано"              # подключённая методика (TubeMethodology) разрешила ядро без остальных блокеров


class GeometryScenario(str, Enum):
    SCENARIO_ANGLE = "сценарий_по_углу_35"
    SCENARIO_HEIGHTS = "сценарий_по_высотам_от_пола"


class DriveLocation(str, Enum):
    """
    Расположение привода вдоль оси транспортёра. Введено 17.09.2026 при
    исправлении находки независимой проверки: п.5 эскиза "Тангенциальная
    песколовка" на самом деле про РАСПОЛОЖЕНИЕ ПРИВОДА ("привод снизу"), а не
    про дренаж — прежняя реализация ошибочно трактовала его как дренажный
    патрубок (`OptionalDetails.drain_connection_required`). Эскиз задаёт это
    ДВУМЯ независимыми источниками — текстом и графикой — которые могут
    расходиться (см. `check_drive_location_conflict`), поэтому это отдельный
    строгий тип, а не поле `drain_connection_required`.
    """

    LOWER_END = "нижний_торец"
    UPPER_END = "верхний_торец"
    UNKNOWN = "неизвестно"


class TubeEngineeringInputError(ValueError):
    """Некорректный ТИП/нечисловое или нераспознанное значение входных данных (не путать с честными блокерами)."""


def _finite_or_none(name: str, value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TubeEngineeringInputError(
            f"{name}: ожидалось число, получено {type(value).__name__} ({value!r})."
        )
    if not math.isfinite(value):
        raise TubeEngineeringInputError(f"{name}: значение должно быть конечным числом, получено {value!r}.")
    return float(value)


def _drive_location_or_none(name: str, value) -> Optional["DriveLocation"]:
    if value is None:
        return None
    if isinstance(value, DriveLocation):
        return value
    if isinstance(value, str):
        try:
            return DriveLocation(value)
        except ValueError:
            pass
    raise TubeEngineeringInputError(
        f"{name}: ожидалось одно из {[e.value for e in DriveLocation]}, получено {value!r}."
    )


@dataclass
class GeometryConflictReport:
    """
    Эскиз "Тангенциальная песколовка (Шнековый транспортёр)" задаёт геометрию
    ДВУМЯ независимыми способами: угол наклона (35°, п.2) + длина по оси
    (2515 мм, п.3) — и высоты загрузки/выгрузки от пола (500/1500 мм, п.6-7).
    Если они не сходятся — это реальное противоречие исходных данных, а не
    ошибка расчёта. Ни один из двух сценариев не выбирается автоматически.
    """

    stated_angle_deg: Optional[float]
    stated_length_along_axis_mm: Optional[float]
    stated_load_height_from_floor_mm: Optional[float]
    stated_unload_height_from_floor_mm: Optional[float]

    height_gain_from_angle_mm: Optional[float]              # length_along_axis * sin(angle)
    horizontal_projection_from_angle_mm: Optional[float]    # length_along_axis * cos(angle)
    height_gain_from_floor_heights_mm: Optional[float]      # unload_height - load_height

    discrepancy_mm: Optional[float]
    discrepancy_percent: Optional[float]
    tolerance_mm: float
    conflict: bool

    scenarios: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def check_geometry_conflict(
    *,
    angle_deg: Optional[float],
    length_along_axis_mm: Optional[float],
    load_height_from_floor_mm: Optional[float],
    unload_height_from_floor_mm: Optional[float],
    tolerance_mm: float = 50.0,
) -> Optional[GeometryConflictReport]:
    """
    Возвращает None, только если данных недостаточно даже для ОДНОГО из двух
    источников геометрии (тогда сравнивать нечего). Если есть хотя бы один
    источник — отчёт формируется (со сценарием(ями), какие удалось посчитать).
    """
    angle_deg = _finite_or_none("Угол наклона", angle_deg)
    length_along_axis_mm = _finite_or_none("Длина по оси", length_along_axis_mm)
    load_height_from_floor_mm = _finite_or_none("Высота загрузки от пола", load_height_from_floor_mm)
    unload_height_from_floor_mm = _finite_or_none("Высота выгрузки от пола", unload_height_from_floor_mm)

    height_gain_from_angle = None
    horizontal_projection_from_angle = None
    if angle_deg is not None and length_along_axis_mm is not None:
        height_gain_from_angle = length_along_axis_mm * math.sin(math.radians(angle_deg))
        horizontal_projection_from_angle = length_along_axis_mm * math.cos(math.radians(angle_deg))

    height_gain_from_heights = None
    if load_height_from_floor_mm is not None and unload_height_from_floor_mm is not None:
        height_gain_from_heights = unload_height_from_floor_mm - load_height_from_floor_mm

    if height_gain_from_angle is None and height_gain_from_heights is None:
        return None

    discrepancy_mm = None
    discrepancy_percent = None
    conflict = False
    notes: list[str] = []

    if height_gain_from_angle is not None and height_gain_from_heights is not None:
        discrepancy_mm = height_gain_from_angle - height_gain_from_heights
        if height_gain_from_heights != 0:
            discrepancy_percent = abs(discrepancy_mm) / abs(height_gain_from_heights) * 100.0
        conflict = abs(discrepancy_mm) > tolerance_mm
        if conflict:
            pct_text = f" ({discrepancy_percent:.0f}% от высоты по полу)" if discrepancy_percent is not None else ""
            notes.append(
                f"ПРОТИВОРЕЧИЕ ГЕОМЕТРИИ: набор высоты по углу {angle_deg:.1f}° и длине "
                f"{length_along_axis_mm:.1f} мм по оси даёт {height_gain_from_angle:.1f} мм, "
                f"а по заявленным высотам пола (загрузка {load_height_from_floor_mm:.0f} мм, "
                f"выгрузка {unload_height_from_floor_mm:.0f} мм) — {height_gain_from_heights:.1f} мм. "
                f"Расхождение {discrepancy_mm:+.1f} мм{pct_text} превышает допуск {tolerance_mm:.0f} мм — "
                "данные эскиза не самосогласованы. Ни один вариант не выбирается автоматически — "
                "см. оба сценария ниже, требуется подтверждение заказчика/Дмитрия Александровича."
            )
        else:
            notes.append(
                f"Геометрия согласована в пределах допуска {tolerance_mm:.0f} мм "
                f"(расхождение {discrepancy_mm:+.1f} мм)."
            )
    elif height_gain_from_angle is not None:
        notes.append("Высоты от пола заданы не полностью — сверка угла 35° с высотами невозможна.")
    else:
        notes.append("Угол и/или длина по оси заданы не полностью — сверка с высотами от пола невозможна.")

    scenarios: dict = {}
    if height_gain_from_angle is not None:
        scenarios[GeometryScenario.SCENARIO_ANGLE.value] = {
            "источник": "п.2-3 эскиза — угол наклона/подключения и длина по оси",
            "angle_deg": angle_deg,
            "length_along_axis_mm": length_along_axis_mm,
            "height_gain_mm": round(height_gain_from_angle, 1),
            "horizontal_projection_mm": (
                round(horizontal_projection_from_angle, 1)
                if horizontal_projection_from_angle is not None else None
            ),
        }
    if height_gain_from_heights is not None:
        scenarios[GeometryScenario.SCENARIO_HEIGHTS.value] = {
            "источник": "п.6-7 эскиза — высоты загрузки/выгрузки от пола",
            "load_height_from_floor_mm": load_height_from_floor_mm,
            "unload_height_from_floor_mm": unload_height_from_floor_mm,
            "height_gain_mm": round(height_gain_from_heights, 1),
        }

    return GeometryConflictReport(
        stated_angle_deg=angle_deg,
        stated_length_along_axis_mm=length_along_axis_mm,
        stated_load_height_from_floor_mm=load_height_from_floor_mm,
        stated_unload_height_from_floor_mm=unload_height_from_floor_mm,
        height_gain_from_angle_mm=round(height_gain_from_angle, 1) if height_gain_from_angle is not None else None,
        horizontal_projection_from_angle_mm=(
            round(horizontal_projection_from_angle, 1) if horizontal_projection_from_angle is not None else None
        ),
        height_gain_from_floor_heights_mm=(
            round(height_gain_from_heights, 1) if height_gain_from_heights is not None else None
        ),
        discrepancy_mm=round(discrepancy_mm, 1) if discrepancy_mm is not None else None,
        discrepancy_percent=round(discrepancy_percent, 1) if discrepancy_percent is not None else None,
        tolerance_mm=tolerance_mm,
        conflict=conflict,
        scenarios=scenarios,
        notes=notes,
    )


@dataclass
class DriveLocationConflictReport:
    """
    Эскиз задаёт расположение привода ДВУМЯ независимыми способами:
    текстовым требованием (п.5 эскиза, уточнено 17.09.2026 — "подключить
    привод снизу шнекового транспортёра") и графической частью (на рисунке
    мотор-редуктор показан у ВЕРХНЕГО торца). Если источники расходятся —
    это реальное противоречие исходных данных, а не ошибка расчёта. Ни один
    из двух источников не выбирается автоматически — по прямой аналогии с
    `GeometryConflictReport`.
    """

    text_location: Optional[DriveLocation]
    text_source: Optional[str]
    graphic_location: Optional[DriveLocation]
    graphic_source: Optional[str]
    conflict: bool
    notes: list[str] = field(default_factory=list)


def check_drive_location_conflict(
    *,
    text_location: Optional[DriveLocation],
    text_source: Optional[str] = None,
    graphic_location: Optional[DriveLocation] = None,
    graphic_source: Optional[str] = None,
) -> Optional[DriveLocationConflictReport]:
    """
    Возвращает None, только если НИ текстовый, ни графический источник не
    заданы вообще (сравнивать нечего). UNKNOWN считается "источник не даёт
    определённого ответа" — сравнение с UNKNOWN конфликтом не считается.
    """
    if text_location is None and graphic_location is None:
        return None

    conflict = False
    notes: list[str] = []
    both_known = (
        text_location is not None and graphic_location is not None
        and text_location != DriveLocation.UNKNOWN and graphic_location != DriveLocation.UNKNOWN
    )
    if both_known and text_location != graphic_location:
        conflict = True
        notes.append(
            "КОНФЛИКТ РАСПОЛОЖЕНИЯ ПРИВОДА: текстовое требование эскиза указывает "
            f"{text_location.value!r}"
            f"{f' (источник: {text_source})' if text_source else ''}, а графическая часть эскиза "
            f"показывает {graphic_location.value!r}"
            f"{f' (источник: {graphic_source})' if graphic_source else ''}. Ни один вариант не "
            "выбирается автоматически — требуется подтверждение заказчика/Дмитрия Александровича, "
            "какой источник верный, прежде чем фиксировать положение привода в компоновке. Выпуск "
            "по этому проекту блокируется до подтверждения."
        )
    elif both_known:
        notes.append("Расположение привода по тексту и графике эскиза согласовано (оба источника совпадают).")
    else:
        notes.append(
            "Расположение привода известно только из одного источника (текст ИЛИ графика эскиза, "
            "не оба) — перекрёстная сверка невозможна, второй источник не задан или UNKNOWN."
        )

    return DriveLocationConflictReport(
        text_location=text_location, text_source=text_source,
        graphic_location=graphic_location, graphic_source=graphic_source,
        conflict=conflict, notes=notes,
    )


@dataclass
class TubeEngineeringInput:
    # Геометрия
    connection_diameter_mm: Optional[float] = None   # DN присоединительного патрубка — НЕ диаметр корпуса
    incline_deg: Optional[float] = None
    working_length_mm: Optional[float] = None         # длина между загрузкой и выгрузкой вдоль оси
    load_height_from_floor_mm: Optional[float] = None
    unload_height_from_floor_mm: Optional[float] = None
    geometry_tolerance_mm: float = 50.0

    # Материал / производительность — раздел "не подставлять неизвестные
    # свойства песка/смеси самостоятельно"
    material_name: Optional[str] = None
    bulk_density_kg_m3: Optional[float] = None
    max_lump_size_mm: Optional[float] = None
    abrasiveness: Optional[str] = None
    is_slurry_mixture: bool = False
    solids_concentration_percent: Optional[float] = None

    productivity_value: Optional[float] = None
    productivity_unit: Optional[str] = None

    # Дренаж — САМОСТОЯТЕЛЬНОЕ требование (подключение дренажного патрубка),
    # НЕ связанное с расположением привода. Не подставлять по умолчанию и не
    # путать с drive_location_* ниже (это была реальная ошибка предыдущего
    # прогона, исправлено 17.09.2026).
    drain_connection_required: Optional[bool] = None

    # Расположение привода (п.5 эскиза, уточнено 17.09.2026) — два независимых
    # источника, см. DriveLocation/check_drive_location_conflict. Принимает
    # строки со значениями DriveLocation.value ("нижний_торец"/"верхний_торец"/
    # "неизвестно") или сами DriveLocation — валидируется в compute_tube_engineering_core.
    drive_location_text: Optional[str] = None
    drive_location_text_source: Optional[str] = None
    drive_location_graphic: Optional[str] = None
    drive_location_graphic_source: Optional[str] = None


@dataclass
class TubeEngineeringResult:
    status: TubeCalcStatus
    geometry_conflict: Optional[GeometryConflictReport] = None
    drive_location_conflict: Optional[DriveLocationConflictReport] = None

    # Инженерная часть — ВСЕГДА Optional; None означает "не вычислено", а
    # НЕ "ноль". Никогда не подставляется методика желобчатого шнека.
    diameter_mm: Optional[float] = None
    step_mm: Optional[float] = None
    rotation_speed_rpm: Optional[float] = None
    shaft_power_kw: Optional[float] = None
    motor_power_kw: Optional[float] = None
    motor_selection_ok: Optional[bool] = None

    # Добавлено 17.09.2026 (этап "стратегия методики") — заранее заведены как
    # Optional-поля результата, чтобы когда подтверждённая методика для трубы
    # на 35° появится, ПОДКЛЮЧЁННАЯ методика (см. TubeMethodology ниже) могла
    # заполнить их без переделки Project/App/Web. Пока методики нет — всегда
    # None (см. UnconfirmedTubeMethodology).
    torque_nm: Optional[float] = None
    starting_torque_nm: Optional[float] = None
    gear_ratio: Optional[float] = None
    bearing_load_radial_n: Optional[float] = None
    bearing_load_axial_n: Optional[float] = None
    mass_kg: Optional[float] = None

    connection_diameter_mm: Optional[float] = None

    # Перевод единиц — не методика, чистая арифметика; считается, когда
    # данных для перевода достаточно (см. compute_tube_engineering_core).
    productivity_required_t_per_h: Optional[float] = None
    productivity_achievable_t_per_h: Optional[float] = None
    requirement_met: Optional[bool] = None

    # Какая методика фактически использовалась ("" — методики нет, честный
    # BLOCKED; иначе имя/версия подключённой методики) — трассируемость.
    methodology_name: str = ""
    methodology_version: str = ""

    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class TubeMethodologyResult:
    """
    Результат ПОДКЛЮЧАЕМОЙ методики расчёта ядра (диаметр/шаг/частота
    вращения/мощность/крутящий момент/...) валового трубчатого шнека.

    Введено 17.09.2026 по прямому указанию задания: "Не реализовывать
    фиктивную методику 35°... подготовить архитектуру так, чтобы при
    появлении методики Project/App/Web НЕ переписывались".

    `resolved=True` означает, что методика САМА посчитала, что ей достаточно
    данных и вернула числа; `resolved=False` — методика подключена, но по
    ЕЁ собственной оценке данных всё ещё не хватает (это не ошибка — методика
    обязана вести себя так же честно, как ядро без неё: без выдуманных чисел).
    Поля с числами при `resolved=False` должны оставаться None.
    """

    resolved: bool = False
    diameter_mm: Optional[float] = None
    step_mm: Optional[float] = None
    rotation_speed_rpm: Optional[float] = None
    shaft_power_kw: Optional[float] = None
    motor_power_kw: Optional[float] = None
    motor_selection_ok: Optional[bool] = None
    torque_nm: Optional[float] = None
    starting_torque_nm: Optional[float] = None
    gear_ratio: Optional[float] = None
    bearing_load_radial_n: Optional[float] = None
    bearing_load_axial_n: Optional[float] = None
    mass_kg: Optional[float] = None
    productivity_achievable_t_per_h: Optional[float] = None
    requirement_met: Optional[bool] = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TubeMethodology:
    """
    Абстрактный интерфейс методики расчёта ядра трубного шнека. Любая
    будущая подтверждённая методика (крутонаклонный/трубный шнек, ~35°)
    реализуется как подкласс этого интерфейса и передаётся в
    `compute_tube_engineering_core(inp, methodology=ИмяМетодики())` —
    никаких изменений в Project/App/Web для этого не требуется: они вызывают
    `compute_tube_engineering_core(inp)` (без аргумента methodology) и
    получат текущую подставленную по умолчанию `UnconfirmedTubeMethodology`,
    либо явно передадут новую методику при её появлении.
    """

    name: str = "неопределена"
    version: str = "0"

    def compute(self, inp: TubeEngineeringInput) -> TubeMethodologyResult:  # pragma: no cover - интерфейс
        raise NotImplementedError


class UnconfirmedTubeMethodology(TubeMethodology):
    """
    Методика ПО УМОЛЧАНИЮ, пока подтверждённой методики для трубного шнека
    на ~35° нет. НЕ выбирает диаметр/шаг/частоту вращения/мощность/момент —
    честно возвращает `resolved=False` и точные блокеры (ровно то поведение,
    что было в этом модуле до введения интерфейса TubeMethodology; вынесено
    сюда без изменения текста блокеров, чтобы не сломать существующие
    тесты/поведение).
    """

    name = "методика_не_подтверждена"
    version = "0"

    def compute(self, inp: TubeEngineeringInput) -> TubeMethodologyResult:
        blockers: list[str] = []

        if inp.connection_diameter_mm is not None:
            dn_note = (
                f"DN{inp.connection_diameter_mm:.0f} — присоединительный диаметр патрубка (п.1 эскиза), "
                "НЕ диаметр корпуса трубного шнека; диаметр корпуса из него не выводится."
            )
        else:
            dn_note = "Присоединительный диаметр (DN) не задан."
        blockers.append(
            f"Диаметр корпуса трубного шнека НЕ определён: {dn_note} Фактический диаметр корпуса "
            "нужно задать отдельно (расчётом по методике или заданием инженера) — здесь не подставляется."
        )

        blockers.append(
            "Методика расчёта производительности/частоты вращения/мощности для ВАЛОВОГО ТРУБЧАТОГО "
            "шнека на угол ~35° отсутствует в этом репозитории. По прямому указанию задания методика "
            "желобчатого шнека (core/screw_engineering.py: incline_correction_c, жёсткий предел 20°, "
            "коэффициенты FILL_FACTOR_PSI/STEP_TO_DIAMETER_RATIO/RESISTANCE_OMEGA/MAX_SPEED_A) для этого "
            "случая не используется. Нужна подтверждённая методика для крутонаклонных/трубных шнеков."
        )

        return TubeMethodologyResult(resolved=False, blockers=blockers)


def _checked_methodology_result(result: TubeMethodologyResult, methodology: TubeMethodology) -> TubeMethodologyResult:
    """Validate the plugin contract before publishing computed values."""
    if not isinstance(result, TubeMethodologyResult):
        return TubeMethodologyResult(blockers=["Методика вернула неподдерживаемый тип результата."])
    if result.resolved is not True:
        # An unresolved plugin must not leak provisional/fabricated numbers into CAD.
        return TubeMethodologyResult(
            blockers=list(result.blockers) or ["Методика не завершила расчёт инженерного ядра."],
            warnings=list(result.warnings),
        )

    errors = []
    for label, value in (("название", methodology.name), ("версия", methodology.version)):
        if not isinstance(value, str) or not value.strip() or value in ("неопределена", "0"):
            errors.append(f"Методика: не указаны подтверждаемые {label}/идентификатор.")
    fields = (
        "diameter_mm", "step_mm", "rotation_speed_rpm", "shaft_power_kw", "motor_power_kw",
        "torque_nm", "starting_torque_nm", "gear_ratio", "bearing_load_radial_n",
        "bearing_load_axial_n", "mass_kg", "productivity_achievable_t_per_h",
    )
    zero_allowed = {"bearing_load_radial_n", "bearing_load_axial_n"}
    for name in fields:
        try:
            value = _finite_or_none(name, getattr(result, name))
        except (TubeEngineeringInputError, OverflowError):
            value = None
        if value is None or value < 0 or (value == 0 and name not in zero_allowed):
            errors.append(f"Методика: {name} отсутствует или имеет недопустимое числовое значение.")
    if errors:
        return TubeMethodologyResult(blockers=list(result.blockers) + errors, warnings=list(result.warnings))
    return result


def compute_tube_engineering_core(
    inp: TubeEngineeringInput, methodology: Optional[TubeMethodology] = None,
) -> TubeEngineeringResult:
    methodology = methodology or UnconfirmedTubeMethodology()
    blockers: list[str] = []
    warnings: list[str] = []

    _finite_or_none("Угол наклона", inp.incline_deg)
    _finite_or_none("Длина по оси", inp.working_length_mm)
    _finite_or_none("Высота загрузки от пола", inp.load_height_from_floor_mm)
    _finite_or_none("Высота выгрузки от пола", inp.unload_height_from_floor_mm)
    _finite_or_none("Присоединительный диаметр", inp.connection_diameter_mm)
    _finite_or_none("Насыпная плотность", inp.bulk_density_kg_m3)
    _finite_or_none("Максимальный размер куска/включения", inp.max_lump_size_mm)
    _finite_or_none("Производительность", inp.productivity_value)
    drive_location_text = _drive_location_or_none("Расположение привода (текст)", inp.drive_location_text)
    drive_location_graphic = _drive_location_or_none("Расположение привода (графика)", inp.drive_location_graphic)

    geometry_conflict = check_geometry_conflict(
        angle_deg=inp.incline_deg,
        length_along_axis_mm=inp.working_length_mm,
        load_height_from_floor_mm=inp.load_height_from_floor_mm,
        unload_height_from_floor_mm=inp.unload_height_from_floor_mm,
        tolerance_mm=inp.geometry_tolerance_mm,
    )
    if geometry_conflict is not None:
        warnings.extend(geometry_conflict.notes)
        if geometry_conflict.conflict:
            blockers.append(
                "Геометрия не самосогласована (угол наклона против заявленных высот пола) — "
                "см. geometry_conflict.scenarios; требуется подтверждение, какой из двух "
                "источников верный, прежде чем фиксировать рабочую длину/угол для компоновки."
            )

    # Диаметр/шаг/частота вращения/мощность/момент — делегируется подключаемой
    # методике (см. TubeMethodology/UnconfirmedTubeMethodology выше, этап
    # "стратегия методики" 17.09.2026). По умолчанию методики нет — ядро
    # получает ровно те же блокеры, что были здесь захардкожены раньше.
    methodology_core = _checked_methodology_result(methodology.compute(inp), methodology)
    blockers.extend(methodology_core.blockers)
    warnings.extend(methodology_core.warnings)
    if methodology_core.resolved:
        if methodology_core.motor_selection_ok is not True:
            blockers.append("Методика не подтвердила подбор двигателя.")
        if methodology_core.requirement_met is not True:
            blockers.append("Методика не подтвердила требуемую производительность.")

    if inp.bulk_density_kg_m3 is None:
        blockers.append(
            "Насыпная/эффективная плотность транспортируемой смеси "
            f"({inp.material_name or 'материал не назван'}) неизвестна — не подставляется "
            "самостоятельно (по прямому указанию задания)."
        )
    if inp.abrasiveness is None:
        blockers.append("Абразивность материала не задана — не подставляется самостоятельно.")
    if inp.max_lump_size_mm is None:
        blockers.append("Максимальный размер включения/куска (в т.ч. твёрдой фракции смеси) не задан.")
    if inp.is_slurry_mixture and inp.solids_concentration_percent is None:
        blockers.append(
            "Материал заявлен как двухфазная смесь (жидкость + твёрдая фаза), но концентрация "
            "твёрдой фазы не задана — влияет на плотность/абразивность/сопротивление и не "
            "подставляется. Признак 'двухфазная смесь' — инженерная интерпретация наименования "
            "материала (статус INFERRED/REQUIRES_CONFIRMATION), а не исходное значение."
        )

    drive_location_conflict = check_drive_location_conflict(
        text_location=drive_location_text,
        text_source=inp.drive_location_text_source,
        graphic_location=drive_location_graphic,
        graphic_source=inp.drive_location_graphic_source,
    )
    if drive_location_conflict is not None:
        warnings.extend(drive_location_conflict.notes)
        if drive_location_conflict.conflict:
            blockers.append(
                "Расположение привода не самосогласовано (текстовое требование против графики "
                "эскиза) — см. drive_location_conflict; требуется подтверждение, какой источник "
                "верный, прежде чем фиксировать положение привода в компоновке."
            )

    productivity_required_t_per_h = None
    if inp.productivity_value is None or inp.productivity_unit is None:
        blockers.append("Требуемая производительность не задана.")
    else:
        unit_n = inp.productivity_unit.strip().lower()
        if unit_n in ("т/ч", "t/h"):
            productivity_required_t_per_h = inp.productivity_value
        elif unit_n in ("кг/ч", "kg/h"):
            productivity_required_t_per_h = inp.productivity_value / 1000.0
        elif unit_n in ("м3/ч", "м³/ч", "m3/h"):
            if inp.bulk_density_kg_m3 is not None and inp.bulk_density_kg_m3 > 0:
                productivity_required_t_per_h = inp.productivity_value * inp.bulk_density_kg_m3 / 1000.0
            else:
                blockers.append(
                    "Производительность задана в м3/ч, плотность неизвестна — перевод в т/ч невозможен."
                )
        else:
            blockers.append(f"Неизвестная единица производительности: {inp.productivity_unit!r}.")

    if (methodology_core.resolved and productivity_required_t_per_h is not None
            and methodology_core.productivity_achievable_t_per_h < productivity_required_t_per_h):
        blockers.append("Достижимая производительность по методике ниже требуемой, независимо от флага requirement_met.")

    if inp.drain_connection_required:
        warnings.append(
            "Указано требование подключения дренажа — не проверено конструктивно (нет CAD-модели "
            "патрубка дренажа, раздел 12). ВАЖНО: это самостоятельное требование, НЕ выводится из "
            "расположения привода (drive_location_*) — п.5 эскиза 'привод снизу' относится к приводу, "
            "не к дренажу (исправлено 17.09.2026, см. TASK.md)."
        )

    # Статус: BLOCKED, если хоть один блокер есть ИЛИ подключённая методика
    # сама не смогла разрешить ядро (resolved=False) — методика без выдуманных
    # чисел ведёт себя так же честно, как ядро без методики. COMPUTED — только
    # когда методика подтверждённо разрешила ядро и других блокеров не осталось
    # (сейчас недостижимо с UnconfirmedTubeMethodology; зарезервировано на
    # момент, когда подтверждённая методика будет подключена).
    status = (
        TubeCalcStatus.COMPUTED
        if methodology_core.resolved and not blockers
        else TubeCalcStatus.BLOCKED
    )

    return TubeEngineeringResult(
        status=status,
        geometry_conflict=geometry_conflict,
        drive_location_conflict=drive_location_conflict,
        diameter_mm=methodology_core.diameter_mm,
        step_mm=methodology_core.step_mm,
        rotation_speed_rpm=methodology_core.rotation_speed_rpm,
        shaft_power_kw=methodology_core.shaft_power_kw,
        motor_power_kw=methodology_core.motor_power_kw,
        motor_selection_ok=methodology_core.motor_selection_ok,
        torque_nm=methodology_core.torque_nm,
        starting_torque_nm=methodology_core.starting_torque_nm,
        gear_ratio=methodology_core.gear_ratio,
        bearing_load_radial_n=methodology_core.bearing_load_radial_n,
        bearing_load_axial_n=methodology_core.bearing_load_axial_n,
        mass_kg=methodology_core.mass_kg,
        connection_diameter_mm=inp.connection_diameter_mm,
        productivity_required_t_per_h=(
            round(productivity_required_t_per_h, 3) if productivity_required_t_per_h is not None else None
        ),
        productivity_achievable_t_per_h=methodology_core.productivity_achievable_t_per_h,
        requirement_met=methodology_core.requirement_met,
        methodology_name=methodology.name,
        methodology_version=methodology.version,
        blockers=blockers,
        warnings=warnings,
    )

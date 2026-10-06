# -*- coding: utf-8 -*-
"""
Минимальный ввод (раздел 6 задания) — Экран 1 "Задача".

Четыре группы: материал, производительность, геометрия, профиль
эксплуатации. Дополнительные вопросы (раздел 6, второй список) вынесены в
OptionalDetails и не запрашиваются, пока явно не понадобятся конкретному
расчёту (сейчас движок их не использует — они зарезервированы для
следующих этапов инженерного ядра и явно помечены как такие).

validate_questionnaire() реализует часть проверок раздела 21: единицы и
диапазоны, противоречивую геометрию, отсутствие свойств материала. Список
проблем возвращается, а не выбрасывается исключением сразу — так интерфейс
может показать всё сразу, а не по одной ошибке за раз.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProductivityUnit(str, Enum):
    KG_H = "кг/ч"
    T_H = "т/ч"
    M3_H = "м3/ч"


class GeometryMode(str, Enum):
    AXIS_LENGTH_ANGLE = "длина_по_оси_и_угол"
    PROJECTION_HEIGHT = "горизонтальная_проекция_и_высота"
    COORDINATES = "координаты_загрузки_выгрузки"


class Abrasiveness(str, Enum):
    LOW = "низкая"
    MEDIUM = "средняя"
    HIGH = "высокая"


class ConveyorKind(str, Enum):
    """Раздел 7 — различие конструкций, разные методики."""

    SHAFTED_TROUGH = "валовый_желобчатый"       # покрыто черновиком ядра (Stage 12)
    SHAFTED_TUBE = "валовый_трубчатый"
    SHAFTLESS = "безваловый"
    FEEDER = "питатель"


@dataclass
class MaterialInput:
    """Группа 1 — транспортируемый материал (не материал конструкции!)."""

    material_name: str
    bulk_density_kg_m3: Optional[float] = None
    max_lump_size_mm: Optional[float] = None
    is_sorted_material: bool = False
    abrasiveness: Optional[Abrasiveness] = None
    # Дополнительные — раздел 6, второй список; заполняются только если нужны
    moisture_percent: Optional[float] = None
    is_fibrous: Optional[bool] = None
    is_sticky: Optional[bool] = None
    temperature_c: Optional[float] = None


@dataclass
class ProductivityInput:
    """
    Группа 2. Оба поля Optional (исправлено 17.09.2026, Issue #3 — находка
    независимой проверки): раньше `value`/`unit` были обязательными, из-за
    чего SHAFTED_TUBE-проекты, где производительность заказчиком ещё не
    названа, были вынуждены подставлять число ради прохождения dataclass —
    что и произошло (фиктивные 5.0 т/ч для TUBE-SAND-001). Для
    SHAFTED_TROUGH производительность остаётся ФАКТИЧЕСКИ обязательной —
    это по-прежнему проверяется в validate_questionnaire() (см.
    productivity_required там), поведение желобчатого шнека не изменилось.
    """

    value: Optional[float] = None
    unit: Optional[ProductivityUnit] = None


@dataclass
class GeometryInput:
    """
    Группа 3. Ровно один способ задания геометрии (mode определяет, какие
    поля значимы). Различаем рабочую длину (working_length_mm, участвует в
    расчёте) и общий габарит (overall_length_mm, для компоновки/чертежа) —
    раздел 6 требует не путать их.
    """

    mode: GeometryMode
    working_length_mm: Optional[float] = None
    incline_deg: Optional[float] = None
    horizontal_projection_mm: Optional[float] = None
    height_gain_mm: Optional[float] = None
    load_point_xyz_mm: Optional[tuple[float, float, float]] = None
    unload_point_xyz_mm: Optional[tuple[float, float, float]] = None
    overall_length_mm: Optional[float] = None  # если ещё не известен — остаётся None

    # Раздел "валовый трубчатый транспортёр" (Issue #3) — дополнительные
    # перекрёстные проверочные поля, независимые от mode. НЕ заменяют
    # working_length_mm/incline_deg, а служат для проверки самосогласованности
    # геометрии (core/tube_engineering.py::check_geometry_conflict).
    connection_diameter_mm: Optional[float] = None  # DN присоединительного патрубка — НЕ диаметр корпуса
    load_height_from_floor_mm: Optional[float] = None
    unload_height_from_floor_mm: Optional[float] = None

    def resolved_length_angle(self) -> tuple[Optional[float], Optional[float]]:
        """Приводит любой из трёх способов задания к (рабочая_длина_мм, угол_град)."""
        if self.mode == GeometryMode.AXIS_LENGTH_ANGLE:
            return self.working_length_mm, self.incline_deg
        if self.mode == GeometryMode.PROJECTION_HEIGHT:
            if self.horizontal_projection_mm is None or self.height_gain_mm is None:
                return None, None
            length = math.hypot(self.horizontal_projection_mm, self.height_gain_mm)
            angle = math.degrees(math.atan2(self.height_gain_mm, self.horizontal_projection_mm))
            return length, angle
        if self.mode == GeometryMode.COORDINATES:
            if self.load_point_xyz_mm is None or self.unload_point_xyz_mm is None:
                return None, None
            dx = self.unload_point_xyz_mm[0] - self.load_point_xyz_mm[0]
            dy = self.unload_point_xyz_mm[1] - self.load_point_xyz_mm[1]
            dz = self.unload_point_xyz_mm[2] - self.load_point_xyz_mm[2]
            horizontal = math.hypot(dx, dy)
            length = math.hypot(horizontal, dz)
            angle = math.degrees(math.atan2(dz, horizontal)) if horizontal > 0 else 90.0
            return length, angle
        return None, None


@dataclass
class OperatingProfileInput:
    """
    Группа 4. Режим/среда/материал конструкции/типовые опции — объединены
    в один "профиль", но каждое принятое по умолчанию значение должно быть
    видимым и подтверждаемым (раздел 6): поэтому accepted_defaults хранит,
    что именно было подставлено автоматически, а не введено пользователем.
    """

    duty_mode: str = "нормальный"          # напр. "нормальный" | "тяжёлый" | "непрерывный"
    environment: str = "цех, без агрессивной среды"
    construction_material: str = "Ст3"     # материал КОНСТРУКЦИИ, не продукта
    typical_options: list[str] = field(default_factory=list)
    accepted_defaults: list[str] = field(default_factory=list)


@dataclass
class OptionalDetails:
    """Раздел 6, второй список — задаются по требованию конкретного расчёта."""

    startup_under_load: Optional[bool] = None
    inlet_backpressure: Optional[bool] = None
    reverse_required: Optional[bool] = None
    multiple_outlets: Optional[bool] = None
    washdown_required: Optional[bool] = None
    special_execution: Optional[str] = None
    dimension_limits_mm: Optional[tuple[float, float, float]] = None
    drive_power_supply: Optional[str] = None

    # Раздел "валовый трубчатый транспортёр" (Issue #3) — поля, нужные для
    # среды "вода/ил с песком" и для трубного расчёта; зарезервированы по
    # тому же принципу, что и остальные поля этого класса (не запрашиваются,
    # пока явно не нужны конкретному расчёту).
    solids_concentration_percent: Optional[float] = None
    duty_hours_per_day: Optional[float] = None
    starts_per_day: Optional[int] = None
    corrosion_requirements: Optional[str] = None
    is_slurry_mixture: Optional[bool] = None
    # Дренаж — САМОСТОЯТЕЛЬНОЕ требование, не связанное с расположением
    # привода (исправлено 17.09.2026: прежде п.5 эскиза "привод снизу"
    # ошибочно трактовался как дренажный патрубок и заполнял именно это
    # поле — см. TASK.md). Не заполнять этим полем требования к приводу.
    drain_connection_required: Optional[bool] = None

    # Расположение привода (Issue #3, добавлено 17.09.2026 по независимой
    # проверке) — эскиз задаёт его ДВУМЯ независимыми источниками (текст +
    # графика), которые могут расходиться; core/tube_engineering.py сверяет
    # их через check_drive_location_conflict(). Значения — строки уровня
    # tube_engineering.DriveLocation ("нижний_торец"/"верхний_торец"/
    # "неизвестно"), валидируются инженерным ядром, а не здесь (по тому же
    # принципу, что и abrasiveness/material — анкета не отклоняет неполные
    # данные для SHAFTED_TUBE, ядро честно возвращает блокер/конфликт).
    drive_location_text: Optional[str] = None
    drive_location_text_source: Optional[str] = None
    drive_location_graphic: Optional[str] = None
    drive_location_graphic_source: Optional[str] = None


@dataclass
class QuestionnaireInput:
    conveyor_kind: ConveyorKind
    material: MaterialInput
    productivity: ProductivityInput
    geometry: GeometryInput
    profile: OperatingProfileInput
    optional: OptionalDetails = field(default_factory=OptionalDetails)
    forced_diameter_mm: Optional[float] = None
    forced_step_mm: Optional[float] = None


def _check_finite(issues: list[str], label: str, value, *, allow_none: bool = True) -> bool:
    """
    Раздел 1.Д: "Отклоняй NaN, Infinity, неверные типы". Возвращает True, если
    значение прошло проверку (можно безопасно применять дальнейшие сравнения
    вроде `<= 0`) — сравнения с NaN в Python всегда дают False, поэтому без
    этой проверки NaN тихо проходил бы как "положительное" значение.
    """
    if value is None:
        return allow_none
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        issues.append(f"{label}: ожидалось число, получено {type(value).__name__} ({value!r}).")
        return False
    if not math.isfinite(value):
        issues.append(f"{label}: значение должно быть конечным числом (не NaN/Infinity), получено {value!r}.")
        return False
    return True


def validate_questionnaire(q: QuestionnaireInput) -> list[str]:
    """
    Возвращает список проблем (пустой список = можно передавать дальше на
    предварительный расчёт). Это НЕ подтверждение инженерных допущений —
    только базовая проверка полноты, единиц и непротиворечивости ввода
    (раздел 21).
    """
    issues: list[str] = []

    # --- материал ---
    if not q.material.material_name or not q.material.material_name.strip():
        issues.append("Не указано наименование транспортируемого материала.")
    # Для SHAFTED_TUBE (Issue #3, "не подставлять неизвестные свойства
    # песка/смеси самостоятельно") отсутствие свойств материала — НЕ причина
    # отказывать в создании проекта: core/tube_engineering.py сам честно
    # вернёт это как блокер расчёта, а не молча посчитает с выдуманными
    # числами. Для SHAFTED_TROUGH требование остаётся жёстким, как было.
    material_props_required = q.conveyor_kind == ConveyorKind.SHAFTED_TROUGH
    if q.material.bulk_density_kg_m3 is None:
        if material_props_required:
            issues.append("Отсутствует насыпная плотность материала — свойство материала не задано.")
    elif _check_finite(issues, "Насыпная плотность", q.material.bulk_density_kg_m3, allow_none=False):
        if q.material.bulk_density_kg_m3 <= 0:
            issues.append(
                f"Насыпная плотность должна быть больше нуля, получено "
                f"{q.material.bulk_density_kg_m3} кг/м3."
            )
    if q.material.max_lump_size_mm is None:
        if material_props_required:
            issues.append("Не указан максимальный размер куска материала.")
    elif _check_finite(issues, "Максимальный размер куска", q.material.max_lump_size_mm, allow_none=False):
        if q.material.max_lump_size_mm < 0:
            issues.append("Максимальный размер куска не может быть отрицательным.")
    if q.material.abrasiveness is None:
        if material_props_required:
            issues.append("Не указана абразивность материала.")
    if _check_finite(issues, "Влажность", q.material.moisture_percent) and q.material.moisture_percent is not None:
        if not (0 <= q.material.moisture_percent <= 100):
            issues.append(f"Влажность вне диапазона 0-100%: {q.material.moisture_percent}.")
    if _check_finite(issues, "Температура продукта", q.material.temperature_c) and q.material.temperature_c is not None:
        if not (-60 <= q.material.temperature_c <= 600):
            issues.append(f"Температура продукта вне разумного диапазона: {q.material.temperature_c} °C.")

    # --- производительность ---
    # SHAFTED_TUBE (Issue #3, исправлено 17.09.2026): производительность может
    # быть НЕИЗВЕСТНА заказчику на этом этапе — она не подставляется фиктивным
    # числом ради прохождения этой проверки (core/tube_engineering.py сам
    # честно вернёт блокер "Требуемая производительность не задана"). Для
    # SHAFTED_TROUGH производительность остаётся ЖЁСТКО обязательной, как и
    # раньше — поведение желобчатого шнека не изменилось ни на байт.
    productivity_required = q.conveyor_kind == ConveyorKind.SHAFTED_TROUGH
    if q.productivity.value is None:
        if productivity_required:
            issues.append("Не указана требуемая производительность.")
    elif _check_finite(issues, "Производительность", q.productivity.value, allow_none=False):
        if q.productivity.value <= 0:
            issues.append(f"Производительность должна быть больше нуля, получено {q.productivity.value}.")

    if q.productivity.value is not None or productivity_required:
        if not isinstance(q.productivity.unit, ProductivityUnit):
            issues.append(f"Неизвестная единица производительности: {q.productivity.unit!r}.")
        elif q.productivity.unit == ProductivityUnit.M3_H and (
            q.material.bulk_density_kg_m3 is None or q.material.bulk_density_kg_m3 <= 0
        ):
            issues.append(
                "Производительность задана в м3/ч, но насыпная плотность неизвестна — "
                "перевод в массовую производительность невозможен."
            )

    # --- геометрия ---
    for label, value in (
        ("Рабочая длина", q.geometry.working_length_mm),
        ("Угол наклона", q.geometry.incline_deg),
        ("Горизонтальная проекция", q.geometry.horizontal_projection_mm),
        ("Набор высоты", q.geometry.height_gain_mm),
        ("Общий габарит", q.geometry.overall_length_mm),
        ("Присоединительный диаметр (DN)", q.geometry.connection_diameter_mm),
        ("Высота загрузки от пола", q.geometry.load_height_from_floor_mm),
        ("Высота выгрузки от пола", q.geometry.unload_height_from_floor_mm),
    ):
        _check_finite(issues, label, value)

    length, angle = q.geometry.resolved_length_angle()
    if length is None or angle is None:
        issues.append(
            f"Геометрия не определена полностью для выбранного способа задания "
            f"({q.geometry.mode.value})."
        )
    elif not math.isfinite(length) or not math.isfinite(angle):
        # NaN/Infinity во входных координатах/длинах даёт NaN здесь, а
        # `nan <= 0` в Python всегда False — без этой проверки такая
        # геометрия молча прошла бы дальше как "положительная длина".
        issues.append(
            f"Геометрия дала нечисловой результат (длина={length!r}, угол={angle!r}) — "
            "проверьте входные координаты/размеры на корректность."
        )
    else:
        if length <= 0:
            issues.append(f"Рабочая длина трассы должна быть больше нуля, получено {length:.1f} мм.")
        # Ограничение 20° — свойство методики ЖЕЛОБЧАТОГО шнека
        # (core/screw_engineering.py::incline_correction_c), а не общее
        # инженерное ограничение. Для SHAFTED_TUBE (Issue #3) круто наклонные
        # углы (напр. 35°) — это ровно тот случай, для которого этот вид
        # конструкции существует; своя методика ещё не подтверждена, но это
        # не проверка диапазона, а честный блокер (core/tube_engineering.py).
        if q.conveyor_kind == ConveyorKind.SHAFTED_TROUGH and (angle < -20 or angle > 20):
            issues.append(
                f"Угол наклона {angle:.1f}° вне диапазона, покрытого текущей методикой "
                f"(до 20° для наклонных — черновик не покрывает круто наклонные/вертикальные шнеки)."
            )
        if (
            q.geometry.overall_length_mm is not None
            and q.geometry.overall_length_mm < length
        ):
            issues.append(
                f"Общий габарит ({q.geometry.overall_length_mm:.0f} мм) меньше рабочей длины "
                f"({length:.0f} мм) — противоречивая геометрия."
            )

    # --- конструкция ---
    if q.conveyor_kind not in (ConveyorKind.SHAFTED_TROUGH, ConveyorKind.SHAFTED_TUBE):
        issues.append(
            f"Вид конструкции {q.conveyor_kind.value!r} — инженерное ядро на этом этапе "
            f"покрывает только {ConveyorKind.SHAFTED_TROUGH.value} и {ConveyorKind.SHAFTED_TUBE.value} "
            "(трубный — только геометрия и честные блокеры, см. core/tube_engineering.py); "
            "расчёт для остальных видов не реализован (раздел 7 — не применять одну методику ко всем)."
        )

    if not q.profile.construction_material or not q.profile.construction_material.strip():
        issues.append("Не указан материал конструкции (это не то же самое, что материал продукта).")

    return issues


def unsupported_requirements(q: QuestionnaireInput) -> list[str]:
    """
    Раздел 1.Г ("неподдерживаемое требование показывай явно, не игнорируй").

    `validate_questionnaire()` проверяет ПОЛНОТУ и непротиворечивость ввода;
    эта функция — отдельная проверка "движок вообще умеет это посчитать".
    Раньше поля OptionalDetails (пуск под нагрузкой, реверс, многоточечная
    выгрузка и т.п.) читались из JSON, но инженерное ядро их нигде не
    использовало — ни расчёта, ни предупреждения не было, требование просто
    молча пропадало. Возвращает список явных предупреждений (не блокирующих
    validate_questionnaire, но обязательных к показу пользователю и записи в
    warnings_log проекта).
    """
    warnings: list[str] = []
    opt = q.optional

    if opt.startup_under_load:
        warnings.append(
            "Указан пуск под нагрузкой — текущее инженерное ядро НЕ рассчитывает пусковой "
            "момент отдельно от рабочего (раздел 4, подбор привода); требование учтено как "
            "заявленное, но не проверено расчётом."
        )
    if opt.inlet_backpressure:
        warnings.append(
            "Указано противодавление на загрузке — текущая методика (раздел 7, черновик) "
            "не моделирует подпор на загрузочном патрубке; требование не проверено расчётом."
        )
    if opt.reverse_required:
        warnings.append(
            "Указан реверс — текущее инженерное ядро и подбор привода не проверяют работу "
            "в реверсивном режиме (циклические нагрузки при реверсе, раздел 3); требование "
            "заявлено, но не покрыто расчётом."
        )
    if opt.multiple_outlets:
        warnings.append(
            "Указана многоточечная выгрузка — геометрическая модель (раздел 6) описывает "
            "одну точку загрузки и одну точку выгрузки; множественная выгрузка не поддержана."
        )
    if opt.washdown_required:
        warnings.append(
            "Указана мойка/влагозащищённое исполнение — нормативный реестр (раздел 8) и "
            "материалы конструкции для этого исполнения не проверены."
        )
    if opt.special_execution:
        warnings.append(
            f"Указано специальное исполнение ({opt.special_execution!r}) — не сопоставлено "
            "ни с одним поддерживаемым видом конструкции (раздел 7)."
        )
    if opt.dimension_limits_mm is not None:
        warnings.append(
            f"Заданы предельные габариты {opt.dimension_limits_mm} — предварительная "
            "компоновка их не проверяет автоматически (нет CAD-синхронизации, раздел 12)."
        )
    if q.conveyor_kind not in (ConveyorKind.SHAFTED_TROUGH, ConveyorKind.SHAFTED_TUBE):
        warnings.append(
            f"Вид конструкции {q.conveyor_kind.value!r} не поддержан инженерным ядром "
            "(см. также validate_questionnaire) — расчёт не будет запущен для этого вида."
        )
    if q.conveyor_kind == ConveyorKind.SHAFTED_TUBE:
        warnings.append(
            "Вид конструкции 'валовый_трубчатый': инженерное ядро (core/tube_engineering.py) "
            "проверяет только геометрию и честно перечисляет блокеры расчёта — методика "
            "производительности/мощности для трубного шнека на крутых углах не подтверждена."
        )
    return warnings

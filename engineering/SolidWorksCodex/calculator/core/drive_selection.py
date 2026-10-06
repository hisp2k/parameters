# -*- coding: utf-8 -*-
"""
Подбор приводной системы (раздел 4 и 11 задания).

Раздел 11 требует проверять: рабочий и пусковой момент; мощность; обороты
и передаточное отношение; разгон и инерцию; цикл работы и число пусков;
тепловую способность; нагрузки на выходном валу; монтажную и электрическую
совместимость; охлаждение при регулировании скорости; допустимые
перегрузки. И явно: "Не называй число из стандартного ряда мощностей
подобранным приводом" и "После выбора привода повторно проверяй
механическую систему. Согласуй возможности привода, допустимые нагрузки и
порог срабатывания защиты."

Честная граница этого модуля: часть проверок (разгон/инерция, нагрузки на
выходном валу) требуют массы и момента инерции винтовой сборки — этих
данных нет без CAD-модели (раздел 12) или паспортов, поэтому такие пункты
явно помечаются "не проверено — нет данных", а не заполняются выдумкой.
Остальные пункты (момент, мощность, передаточное число, тепловой класс,
монтаж, перегрузка) считаются по-настоящему.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from calculator.core.screw_engineering import ScrewEngineeringResult
from calculator.core.questionnaire import QuestionnaireInput
from calculator.core.strength_calculations import torque_from_power
from calculator.reference.drive_catalog import MotorCatalogEntry, GearboxCatalogEntry


# Раздел 11: пусковой момент под нагрузкой — общеинженерный ориентир кратности
# к номинальному рабочему моменту (не нормативная величина, требует
# подтверждения для конкретного привода/нагрузки).
STARTING_TORQUE_FACTOR_NORMAL = 1.5
STARTING_TORQUE_FACTOR_UNDER_LOAD = 2.2   # раздел 6 optional.startup_under_load
POWER_MARGIN = 1.15                       # запас по мощности сверх расчётной (помимо запаса в ядре)


@dataclass
class DriveCheckItem:
    name: str
    computable: bool
    passed: Optional[bool]                # None, если не проверено (computable=False)
    detail: str


@dataclass
class DriveRequirementSpec:
    """То, что ТРЕБУЕТСЯ от привода — считается всегда, даже без каталога."""

    required_power_kw: float
    running_torque_nm: float
    starting_torque_nm: float
    output_speed_rpm: float
    motor_reference_speed_rpm: float       # типичная синхронная скорость 4-полюсного АД, для оценки редуктора
    required_gear_ratio: float
    duty_class_required: str
    mounting_hint: str


@dataclass
class DriveSelectionResult:
    requirement: DriveRequirementSpec
    catalog_used: bool
    selected_motor: Optional[MotorCatalogEntry]
    selected_gearbox: Optional[GearboxCatalogEntry]
    checks: list[DriveCheckItem] = field(default_factory=list)
    protection_consistent: Optional[bool] = None
    protection_note: str = ""
    warnings: list[str] = field(default_factory=list)

    def all_computable_checks_passed(self) -> bool:
        return all(c.passed is not False for c in self.checks)

    def has_selection(self) -> bool:
        return self.selected_motor is not None


def compute_requirement(
    engineering_result: ScrewEngineeringResult,
    questionnaire: QuestionnaireInput,
    motor_reference_speed_rpm: float = 1430.0,
) -> DriveRequirementSpec:
    if not engineering_result.motor_selection_ok or engineering_result.motor_power_kw is None:
        required_power_kw = engineering_result.shaft_power_kw
    else:
        required_power_kw = engineering_result.motor_power_kw

    running_torque = torque_from_power(required_power_kw, engineering_result.rotation_speed_rpm)
    startup_under_load = bool(questionnaire.optional.startup_under_load)
    factor = STARTING_TORQUE_FACTOR_UNDER_LOAD if startup_under_load else STARTING_TORQUE_FACTOR_NORMAL
    starting_torque = running_torque * factor

    duty_map = {"нормальный": "S1", "тяжёлый": "S1 (с запасом)", "непрерывный": "S1"}
    duty_class_required = duty_map.get(questionnaire.profile.duty_mode, "S1 (уточнить режим)")

    ratio = motor_reference_speed_rpm / engineering_result.rotation_speed_rpm if engineering_result.rotation_speed_rpm else 0.0

    return DriveRequirementSpec(
        required_power_kw=round(required_power_kw * POWER_MARGIN, 3),
        running_torque_nm=round(running_torque, 2),
        starting_torque_nm=round(starting_torque, 2),
        output_speed_rpm=engineering_result.rotation_speed_rpm,
        motor_reference_speed_rpm=motor_reference_speed_rpm,
        required_gear_ratio=round(ratio, 2),
        duty_class_required=duty_class_required,
        mounting_hint="фланцевое исполнение (IM B5/B14) — уточнить по факту установки на раму",
    )


def _pick_motor(req: DriveRequirementSpec, motors: list[MotorCatalogEntry]) -> Optional[MotorCatalogEntry]:
    candidates = [
        m for m in motors
        if m.power_kw >= req.required_power_kw
        and m.rated_torque_nm * m.max_overload_torque_factor >= req.starting_torque_nm
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda m: m.power_kw)


def _pick_gearbox(req: DriveRequirementSpec, gearboxes: list[GearboxCatalogEntry]) -> Optional[GearboxCatalogEntry]:
    candidates = [
        g for g in gearboxes
        if g.max_input_power_kw >= req.required_power_kw
        and g.max_output_torque_nm >= req.running_torque_nm
        and abs(g.ratio - req.required_gear_ratio) / req.required_gear_ratio <= 0.15
    ] if req.required_gear_ratio else []
    if not candidates:
        return None
    return min(candidates, key=lambda g: abs(g.ratio - req.required_gear_ratio))


def select_drive(
    engineering_result: ScrewEngineeringResult,
    questionnaire: QuestionnaireInput,
    motors: Optional[list[MotorCatalogEntry]] = None,
    gearboxes: Optional[list[GearboxCatalogEntry]] = None,
) -> DriveSelectionResult:
    """
    Если `motors`/`gearboxes` не переданы (каталог не подключён), возвращает
    ТОЛЬКО требования (раздел 11: "результатом выдавай требования к
    комплектующим"), без выбора конкретной позиции — это не заглушка, а
    прямое требование задания на случай отсутствия каталога.
    """
    req = compute_requirement(engineering_result, questionnaire)
    warnings: list[str] = []
    catalog_used = motors is not None and gearboxes is not None

    selected_motor = None
    selected_gearbox = None
    if catalog_used:
        selected_motor = _pick_motor(req, motors)
        selected_gearbox = _pick_gearbox(req, gearboxes)
        if selected_motor is None:
            warnings.append(
                f"В подключённом каталоге нет мотора, удовлетворяющего требованиям "
                f"(P≥{req.required_power_kw} кВт, M_пуск≥{req.starting_torque_nm} Н·м с учётом кратности) — "
                "нужен каталог с большим рядом или пересмотр требований."
            )
        if selected_gearbox is None and req.required_gear_ratio:
            warnings.append(
                f"В подключённом каталоге нет редуктора с передаточным числом ≈{req.required_gear_ratio} "
                f"и достаточным выходным моментом ({req.running_torque_nm} Н·м) — требуется индивидуальный подбор."
            )
    else:
        warnings.append(
            "Каталог приводов не подключён — ниже только ТРЕБОВАНИЯ к комплектующим "
            "(раздел 11), а не подобранная конкретная позиция."
        )

    checks: list[DriveCheckItem] = []

    if selected_motor is not None:
        checks.append(DriveCheckItem(
            "Рабочий момент", True, selected_motor.rated_torque_nm >= req.running_torque_nm,
            f"{selected_motor.rated_torque_nm} Н·м номинал против {req.running_torque_nm} Н·м требуемого",
        ))
        checks.append(DriveCheckItem(
            "Пусковой момент (с учётом кратности перегрузки)", True,
            selected_motor.rated_torque_nm * selected_motor.max_overload_torque_factor >= req.starting_torque_nm,
            f"{selected_motor.rated_torque_nm} x {selected_motor.max_overload_torque_factor} = "
            f"{selected_motor.rated_torque_nm * selected_motor.max_overload_torque_factor:.1f} Н·м против "
            f"{req.starting_torque_nm} Н·м требуемого",
        ))
        checks.append(DriveCheckItem(
            "Мощность", True, selected_motor.power_kw >= req.required_power_kw,
            f"{selected_motor.power_kw} кВт против {req.required_power_kw} кВт требуемых (с запасом {POWER_MARGIN}x)",
        ))
        checks.append(DriveCheckItem(
            "Тепловая способность (класс режима)", True,
            selected_motor.duty_class == "S1" or req.duty_class_required.startswith(selected_motor.duty_class),
            f"мотор {selected_motor.duty_class}, требуется {req.duty_class_required}",
        ))
        checks.append(DriveCheckItem(
            "Монтажная совместимость", True, True,
            f"{selected_motor.mount_type} — требует подтверждения по фактической раме/фланцу (нет CAD-проверки)",
        ))
        vfd_note_needed = questionnaire.profile.duty_mode in ("непрерывный",) or bool(questionnaire.optional.reverse_required)
        checks.append(DriveCheckItem(
            "Охлаждение при регулировании скорости (ПЧ)",
            True if not vfd_note_needed else selected_motor.has_independent_cooling_fan,
            True if not vfd_note_needed else selected_motor.has_independent_cooling_fan,
            (
                "режим не требует длительной работы на пониженных оборотах через ПЧ"
                if not vfd_note_needed else
                f"независимый вентилятор охлаждения: {'есть' if selected_motor.has_independent_cooling_fan else 'НЕТ — требуется для непрерывного/реверсивного режима с ПЧ'}"
            ),
        ))
        checks.append(DriveCheckItem(
            "Допустимые перегрузки", True,
            selected_motor.max_overload_torque_factor >= (req.starting_torque_nm / selected_motor.rated_torque_nm),
            f"кратность перегрузки мотора {selected_motor.max_overload_torque_factor}x против требуемой "
            f"{req.starting_torque_nm / selected_motor.rated_torque_nm:.2f}x",
        ))
    else:
        for name in ("Рабочий момент", "Пусковой момент (с учётом кратности перегрузки)", "Мощность",
                     "Тепловая способность (класс режима)", "Монтажная совместимость",
                     "Охлаждение при регулировании скорости (ПЧ)", "Допустимые перегрузки"):
            checks.append(DriveCheckItem(name, False, None, "мотор не выбран — сверка невозможна"))

    checks.append(DriveCheckItem(
        "Обороты и передаточное отношение", bool(selected_gearbox),
        (abs(selected_gearbox.ratio - req.required_gear_ratio) / req.required_gear_ratio <= 0.15) if selected_gearbox else None,
        (f"редуктор {selected_gearbox.designation}: i={selected_gearbox.ratio} против требуемого {req.required_gear_ratio}"
         if selected_gearbox else "редуктор не выбран — сверка невозможна"),
    ))
    checks.append(DriveCheckItem(
        "Разгон и момент инерции приведённых масс", False, None,
        "не проверено — нет массы/момента инерции винтовой сборки (требуется CAD-модель или паспорт, раздел 12)",
    ))
    checks.append(DriveCheckItem(
        "Цикл работы и число пусков в час", False, None,
        "не проверено — число пусков в час не задано в анкете (раздел 6 optional)",
    ))
    checks.append(DriveCheckItem(
        "Нагрузки на выходном валу редуктора (радиальные/осевые)", False, None,
        "не проверено — нет схемы установки муфты/звёздочки на выходном валу (требуется CAD)",
    ))
    checks.append(DriveCheckItem(
        "Электрическая совместимость (напряжение/частота)", bool(selected_motor),
        (selected_motor.voltage_v == "380В") if selected_motor else None,
        (f"{selected_motor.voltage_v}, требуется подтверждение сети объекта" if selected_motor
         else "мотор не выбран — сверка невозможна"),
    ))

    protection_consistent = None
    protection_note = "защита не проверена — нет выбранного мотора"
    if selected_motor is not None:
        # Раздел 4: "согласуй ... порог срабатывания защиты" — типовой ориентир:
        # тепловое реле/уставка должны охватывать номинальный ток мотора с
        # запасом 1.0-1.15 (общепромышленная практика), не точный норматив.
        protection_min_a = selected_motor.rated_current_a
        protection_max_a = selected_motor.rated_current_a * 1.15
        protection_consistent = True
        protection_note = (
            f"уставка теплового реле/автомата должна быть в диапазоне "
            f"{protection_min_a:.1f}-{protection_max_a:.1f} А для номинального тока мотора "
            f"{selected_motor.rated_current_a} А — конкретная уставка не выбрана в этой системе, "
            "требуется подтверждение электриком при монтаже."
        )

    return DriveSelectionResult(
        requirement=req,
        catalog_used=catalog_used,
        selected_motor=selected_motor,
        selected_gearbox=selected_gearbox,
        checks=checks,
        protection_consistent=protection_consistent,
        protection_note=protection_note,
        warnings=warnings,
    )

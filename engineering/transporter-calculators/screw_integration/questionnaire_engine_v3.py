"""Deterministic calculation orchestration for questionnaire-driven v3."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from questionnaire_parser_v3 import ExtractionResult, ExtractedField, apply_defaults
from questionnaire_schema_v3 import BELT_REQUIRED, FIELD_MAP, ROLLER_REQUIRED_BASE
from transporter_core_v2 import (
    BeltInput,
    RollerInput,
    COMPLEXITY_FACTORS,
    STEEL_GRADES,
    calc_belt,
    calc_belt_advanced,
    calc_belt_economics,
    calc_frame,
    calc_roller,
    calc_roller_drive_selection,
    calc_roller_economics,
)


@dataclass
class CalculationPackage:
    status: str
    product_type: Optional[str]
    missing_required: List[str]
    warnings: List[str]
    assumptions: List[str]
    audit: List[Dict[str, Any]]
    engineering: Dict[str, Any]
    economics: Dict[str, Any]
    bom: List[Dict[str, Any]]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, default=str)


def _v(fields: Dict[str, ExtractedField], key: str, default: Any = None) -> Any:
    return fields[key].value if key in fields else default


def validate_extraction(result: ExtractionResult) -> List[str]:
    fields = result.fields
    ptype = result.product_type or _v(fields, "product_type")
    missing: List[str] = []
    if ptype not in {"Ленточный конвейер", "Рольганг"}:
        return ["product_type"]
    required = BELT_REQUIRED if ptype == "Ленточный конвейер" else ROLLER_REQUIRED_BASE
    for key in required:
        if key == "product_type":
            continue
        if key not in fields or fields[key].value in (None, ""):
            missing.append(key)
    if ptype == "Рольганг":
        shape = _v(fields, "cargo_shape")
        if shape == "Прямоугольный груз":
            for key in ("cargo_length_mm", "cargo_width_mm"):
                if key not in fields or not _v(fields, key):
                    missing.append(key)
        elif shape == "Цилиндрический груз":
            for key in ("cylinder_diameter_mm", "cylinder_axial_length_mm"):
                if key not in fields or not _v(fields, key):
                    missing.append(key)
        else:
            if "cargo_shape" not in missing:
                missing.append("cargo_shape")
    return list(dict.fromkeys(missing))


def validate_values(result: ExtractionResult) -> List[str]:
    """Reject invalid values before they reach engineering formulae."""
    errors = []
    positive = {"capacity_tph", "length_m", "conveyor_length_m", "bulk_density_t_m3",
                "carry_spacing_m", "return_spacing_m", "frame_support_span_m", "cargo_mass_kg"}
    shape = _v(result.fields, "cargo_shape")
    if result.product_type == "Рольганг":
        positive.update({"cargo_length_mm", "cargo_width_mm"} if shape == "Прямоугольный груз"
                        else {"cylinder_diameter_mm", "cylinder_axial_length_mm"})
    ranges = {"incline_deg": (0, 24), "repose_angle_deg": (5, 60),
              "dynamic_load_factor": (1, 10)}
    for key, field in result.fields.items():
        meta = FIELD_MAP.get(key)
        if not meta:
            continue
        value = field.value
        if meta.dtype in {"float", "int"}:
            try:
                n = float(value)
                if isinstance(value, bool) or not math.isfinite(n):
                    raise ValueError()
            except (ValueError, TypeError):
                errors.append(f"{meta.title}: введите конечное число")
                continue
            if n < 0 or (key in positive and n <= 0):
                errors.append(f"{meta.title}: должно быть {'больше нуля' if key in positive else 'неотрицательным'}")
            if key in ranges and not ranges[key][0] <= n <= ranges[key][1]:
                errors.append(f"{meta.title}: поддерживаемый диапазон {ranges[key][0]}–{ranges[key][1]}")
            if key == "trough_angle_deg" and n not in (20, 30):
                errors.append("Угол желобчатости: эта модель поддерживает только 20 и 30°")
        elif meta.dtype == "enum" and meta.allowed and value not in meta.allowed:
            errors.append(f"{meta.title}: выберите значение из списка")
        elif meta.dtype == "bool" and not isinstance(value, bool):
            errors.append(f"{meta.title}: выберите да или нет")
    if result.product_type == "Рольганг" and _v(result.fields, "conveyor_type") == "Приводной":
        if _v(result.fields, "speed_mps", 0) == 0:
            errors.append("Для приводного рольганга скорость должна быть больше нуля")
    return errors


def engineering_blockers(engineering: Dict[str, Any]) -> List[str]:
    issues = []
    if engineering.get("frame") and not engineering["frame"].get("section"):
        issues.append("Не подобран профиль рамы: требуется специальный расчёт")
    required = {"belt": ["selected_width_mm", "selected_motor_kw"],
                "advanced": ["selected_plies", "drive_drum_diameter_mm", "tail_drum_diameter_mm", "gearbox_ratio_selected"],
                "roller": ["selected_diameter_mm", "selected_roller_length_mm", "selected_pitch_mm"]}
    for part, names in required.items():
        if part in engineering and any(not engineering[part].get(k) for k in names):
            issues.append("Не все узлы подобраны из справочного ряда: требуется инженерная проверка")
    if "roller" in engineering and engineering["input"].get("conveyor_type") == "Приводной":
        if not engineering["roller"].get("selected_motor_kw"):
            issues.append("Не подобран привод рольганга")
    return list(dict.fromkeys(issues))


def missing_titles(keys: List[str]) -> List[str]:
    return [f"{FIELD_MAP[k].title} ({FIELD_MAP[k].unit})" if k in FIELD_MAP and FIELD_MAP[k].unit else FIELD_MAP[k].title if k in FIELD_MAP else k for k in keys]


def _assumptions(result: ExtractionResult) -> List[str]:
    return [f"{FIELD_MAP[k].title}: {v.value} — принято по умолчанию" for k, v in result.fields.items() if v.origin == "default" and k in FIELD_MAP]


def _belt_package(result: ExtractionResult) -> CalculationPackage:
    f = result.fields
    inp = BeltInput(
        capacity_tph=float(_v(f, "capacity_tph")),
        length_m=float(_v(f, "length_m")),
        incline_deg=float(_v(f, "incline_deg")),
        bulk_density_t_m3=float(_v(f, "bulk_density_t_m3")),
        repose_angle_deg=float(_v(f, "repose_angle_deg")),
        service_category=str(_v(f, "service_category", "Средние")),
        abrasiveness=str(_v(f, "abrasiveness", "Средняя")),
        dustiness=str(_v(f, "dustiness", "Низкая")),
        max_lump_mm=float(_v(f, "max_lump_mm", 0.0)),
        fragile_cargo=bool(_v(f, "fragile_cargo", False)),
        trough_angle_deg=int(_v(f, "trough_angle_deg", 30)),
        carrying_idler_spacing_m=float(_v(f, "carry_spacing_m", 1.2)),
    )
    belt = calc_belt(inp)
    adv = calc_belt_advanced(
        belt,
        inp,
        special_execution=str(_v(f, "special_execution", "Общего назначения")),
    )
    external_line_mass = (
        belt.conveyed_mass_kg_m + 2.0 * belt.belt_mass_kg_m +
        belt.carry_rotating_mass_kg_m + belt.return_rotating_mass_kg_m
    )
    steel = str(_v(f, "frame_steel_grade", "09Г2С (предварительно)"))
    if steel not in STEEL_GRADES:
        steel = "09Г2С (предварительно)"
    frame = calc_frame(
        conveyor_length_m=inp.length_m,
        external_line_mass_kg_m_total=external_line_mass,
        support_span_m=float(_v(f, "frame_support_span_m", 2.0)),
        steel_yield_mpa=STEEL_GRADES[steel],
    )

    econ_dict: Dict[str, Any] = {}
    hourly = _v(f, "hourly_rate_rub")
    if hourly is not None and float(hourly) > 0:
        complexity = str(_v(f, "complexity", "Стандартный цех"))
        econ = calc_belt_economics(
            belt=belt,
            conveyor_length_m=inp.length_m,
            hourly_rate_rub=float(hourly),
            complexity_factor=COMPLEXITY_FACTORS.get(complexity, 1.0),
            price_frame_m=float(_v(f, "price_frame_m", 0.0)),
            price_belt_m=float(_v(f, "price_belt_m", 0.0)),
            price_roller_pc=float(_v(f, "price_roller_pc", 0.0)),
            price_motor=float(_v(f, "price_motor", 0.0)),
            extra_components=float(_v(f, "extra_components", 0.0)),
            frame_h_m=float(_v(f, "belt_frame_h_m", 0.80)),
            drive_station_h=float(_v(f, "belt_drive_h", 6.0)),
            tension_station_h=float(_v(f, "belt_tension_h", 4.0)),
            roller_h_pc=float(_v(f, "belt_roller_h_pc", 0.10)),
            belt_install_h_m=float(_v(f, "belt_install_h_m", 0.12)),
            carry_spacing_m=float(_v(f, "carry_spacing_m", 1.2)),
            return_spacing_m=float(_v(f, "return_spacing_m", 2.5)),
            belt_length_reserve_pct=3.0,
        )
        econ_dict = asdict(econ)

    carry_sets = int(inp.length_m / max(float(_v(f, "carry_spacing_m", 1.2)), 0.1)) + 2
    return_rollers = int(inp.length_m / max(float(_v(f, "return_spacing_m", 2.5)), 0.1)) + 2
    belt_len = 2.0 * inp.length_m * 1.03
    bom = [
        {"Позиция": "Лента конвейерная", "Кол-во": round(belt_len, 2), "Ед.": "м", "Параметр": f"B={belt.selected_width_mm or belt.theoretical_width_mm:.0f} мм; {adv.selected_plies or '?'}×{adv.selected_fabric or 'спец.'}"},
        {"Позиция": "Грузовая роликоопора", "Кол-во": carry_sets, "Ед.": "компл.", "Параметр": f"B={belt.selected_width_mm or belt.theoretical_width_mm:.0f} мм; ролик Ø{adv.selected_idler_diameter_mm or 0} мм"},
        {"Позиция": "Ролик холостой ветви", "Кол-во": return_rollers, "Ед.": "шт", "Параметр": f"B={belt.selected_width_mm or belt.theoretical_width_mm:.0f} мм; Ø{adv.selected_idler_diameter_mm or 0} мм"},
        {"Позиция": "Барабан приводной", "Кол-во": 1, "Ед.": "шт", "Параметр": f"Ø{adv.drive_drum_diameter_mm or 0}×{adv.drum_shell_length_mm or 0} мм"},
        {"Позиция": "Барабан хвостовой/натяжной", "Кол-во": 1, "Ед.": "шт", "Параметр": f"Ø{adv.tail_drum_diameter_mm or 0}×{adv.drum_shell_length_mm or 0} мм"},
        {"Позиция": "Электродвигатель", "Кол-во": 1, "Ед.": "шт", "Параметр": f"{belt.selected_motor_kw or belt.design_motor_power_kw:.2f} кВт"},
        {"Позиция": "Редуктор", "Кол-во": 1, "Ед.": "шт", "Параметр": f"i≈{adv.gearbox_ratio_selected or adv.gearbox_ratio_required or 0:.2f}"},
        {"Позиция": "Продольная балка рамы", "Кол-во": round(inp.length_m * 2, 2), "Ед.": "м", "Параметр": frame.section or "требуется специальный расчет"},
    ]
    warnings = list(result.warnings) + belt.warnings + adv.warnings + frame.warnings
    warnings.append("Спецификация содержит основные узлы. Опоры, связи, крепёж, ограждения и электрика требуют дополнения по проекту.")
    engineering = {
        "input": asdict(inp),
        "belt": asdict(belt),
        "advanced": asdict(adv),
        "frame": asdict(frame),
    }
    return CalculationPackage("calculated", "Ленточный конвейер", [], warnings, _assumptions(result), result.audit_rows(), engineering, econ_dict, bom)


def _roller_package(result: ExtractionResult) -> CalculationPackage:
    f = result.fields
    inp = RollerInput(
        conveyor_length_m=float(_v(f, "conveyor_length_m")),
        cargo_shape=str(_v(f, "cargo_shape")),
        cargo_length_mm=float(_v(f, "cargo_length_mm", 0.0) or 0.0),
        cargo_width_mm=float(_v(f, "cargo_width_mm", 0.0) or 0.0),
        cargo_height_mm=float(_v(f, "cargo_height_mm", 0.0) or 0.0),
        cylinder_diameter_mm=float(_v(f, "cylinder_diameter_mm", 0.0) or 0.0),
        cylinder_axial_length_mm=float(_v(f, "cylinder_axial_length_mm", 0.0) or 0.0),
        cargo_mass_kg=float(_v(f, "cargo_mass_kg")),
        speed_mps=float(_v(f, "speed_mps")),
        conveyor_type="Приводной" if _v(f, "conveyor_type") == "Приводной" else "Гравитационный/неприводной",
        side_clearance_each_mm=float(_v(f, "side_clearance_each_mm", 50.0)),
        dynamic_load_factor=float(_v(f, "dynamic_load_factor", 1.25)),
        load_gap_mm=float(_v(f, "load_gap_mm", 100.0)),
    )
    roller = calc_roller(inp)
    drive = calc_roller_drive_selection(roller, inp.speed_mps)
    rotating_total = (roller.estimated_rotating_mass_kg or 0.0) * roller.roller_count
    live_mass_per_m = roller.simultaneous_loads * inp.cargo_mass_kg / max(inp.conveyor_length_m, 0.001)
    roller_mass_per_m = rotating_total / max(inp.conveyor_length_m, 0.001)
    steel = str(_v(f, "frame_steel_grade", "09Г2С (предварительно)"))
    if steel not in STEEL_GRADES:
        steel = "09Г2С (предварительно)"
    frame = calc_frame(
        conveyor_length_m=inp.conveyor_length_m,
        external_line_mass_kg_m_total=live_mass_per_m + roller_mass_per_m,
        support_span_m=float(_v(f, "frame_support_span_m", 2.0)),
        steel_yield_mpa=STEEL_GRADES[steel],
    )

    econ_dict: Dict[str, Any] = {}
    hourly = _v(f, "hourly_rate_rub")
    if hourly is not None and float(hourly) > 0:
        complexity = str(_v(f, "complexity", "Стандартный цех"))
        econ = calc_roller_economics(
            roller=roller,
            conveyor_length_m=inp.conveyor_length_m,
            conveyor_type=inp.conveyor_type,
            hourly_rate_rub=float(hourly),
            complexity_factor=COMPLEXITY_FACTORS.get(complexity, 1.0),
            price_frame_m=float(_v(f, "price_frame_m", 0.0)),
            price_roller_pc=float(_v(f, "price_roller_pc", 0.0)),
            price_motor=float(_v(f, "price_motor", 0.0)),
            extra_components=float(_v(f, "extra_components", 0.0)),
            frame_h_m=float(_v(f, "roller_frame_h_m", 0.60)),
            roller_h_pc=float(_v(f, "roller_roller_h_pc", 0.12)),
            drive_station_h=float(_v(f, "roller_drive_h", 4.0)),
            adjustment_h_m=float(_v(f, "roller_adjustment_h_m", 0.15)),
        )
        econ_dict = asdict(econ)

    bom = [
        {"Позиция": "Ролик", "Кол-во": roller.roller_count, "Ед.": "шт", "Параметр": f"Ø{roller.selected_diameter_mm or 0}×{roller.selected_roller_length_mm or 0}; шаг {roller.selected_pitch_mm or 0} мм"},
        {"Позиция": "Продольная балка рамы", "Кол-во": round(inp.conveyor_length_m * 2, 2), "Ед.": "м", "Параметр": frame.section or "требуется специальный расчет"},
    ]
    if inp.conveyor_type == "Приводной":
        bom.extend([
            {"Позиция": "Электродвигатель", "Кол-во": 1, "Ед.": "шт", "Параметр": f"{roller.selected_motor_kw or roller.design_motor_power_kw:.2f} кВт"},
            {"Позиция": "Редуктор", "Кол-во": 1, "Ед.": "шт", "Параметр": f"i≈{drive.get('ratio_selected') or drive.get('ratio_required') or 0:.2f}; M≈{drive.get('torque_nm') or 0:.1f} Н·м"},
        ])
    warnings = list(result.warnings) + roller.warnings + frame.warnings
    warnings.append("Спецификация содержит основные узлы. Опоры, связи, крепёж, ограждения и электрика требуют дополнения по проекту.")
    engineering = {
        "input": asdict(inp),
        "roller": asdict(roller),
        "drive": drive,
        "frame": asdict(frame),
    }
    return CalculationPackage("calculated", "Рольганг", [], warnings, _assumptions(result), result.audit_rows(), engineering, econ_dict, bom)


def calculate_from_extraction(raw_result: ExtractionResult, use_defaults: bool = True) -> CalculationPackage:
    result = apply_defaults(raw_result) if use_defaults else raw_result
    missing = validate_extraction(result) + validate_values(result)
    if missing:
        return CalculationPackage(
            status="needs_input",
            product_type=result.product_type,
            missing_required=missing_titles(missing),
            warnings=list(result.warnings),
            assumptions=_assumptions(result),
            audit=result.audit_rows(),
            engineering={},
            economics={},
            bom=[],
        )
    try:
        if result.product_type == "Ленточный конвейер":
            return _belt_package(result)
        return _roller_package(result)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        return CalculationPackage("needs_input", result.product_type, [f"Проверьте исходные данные: {exc}"],
                                  list(result.warnings), _assumptions(result), result.audit_rows(), {}, {}, [])

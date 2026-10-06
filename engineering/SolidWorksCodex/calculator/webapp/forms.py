# -*- coding: utf-8 -*-
"""
Разбор HTML-форм веб-интерфейса (раздел 2 задания) в типизированные модели
`core/questionnaire.py` — единственное место, которое знает про имена полей
формы, чтобы маршруты `webapp/app.py` оставались тонкими и не дублировали
разбор данных.

Раздел 2 требует: "пользователь никогда не редактирует JSON напрямую" —
поэтому здесь нет ни одного места, где сырой JSON проекта показывается или
принимается от пользователя; вход — только именованные поля формы.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails, Abrasiveness,
)
from calculator.core.tube_engineering import DriveLocation

DESIGNATION_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class FormError(Exception):
    """Ошибка разбора формы — показывается пользователю по-русски как есть."""


def parse_designation(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not DESIGNATION_RE.match(raw):
        raise FormError(
            "Обозначение проекта должно содержать только латинские буквы, цифры, "
            "символы '_' и '-' (от 1 до 80 символов) — оно используется как имя файла проекта."
        )
    return raw


def _float_or_none(raw: str | None) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(str(raw).strip().replace(",", "."))
    except ValueError:
        raise FormError(f"Ожидалось число, получено {raw!r}.")


def _float_required(raw: str | None, label: str) -> float:
    value = _float_or_none(raw)
    if value is None:
        raise FormError(f"Поле «{label}» обязательно для заполнения.")
    return value


def _int_or_none(raw: str | None) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        raise FormError(f"Ожидалось целое число, получено {raw!r}.")


def _checkbox(form: Mapping[str, Any], name: str) -> bool:
    return form.get(name) in ("on", "true", "1", "да", True)


def _optional_bool(form: Mapping[str, Any], name: str) -> bool | None:
    raw = form.get(name, "")
    if raw in ("", "не_указано", None):
        return None
    return raw in ("on", "true", "1", "да", True)


def _enum_or_error(enum_cls, raw: str | None, label: str, default=None):
    if raw is None or raw == "":
        if default is not None:
            return default
        raise FormError(f"Поле «{label}» обязательно для заполнения.")
    try:
        return enum_cls(raw)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise FormError(f"Недопустимое значение поля «{label}»: {raw!r}. Допустимо: {allowed}.")


def questionnaire_from_form(form: Mapping[str, Any]) -> QuestionnaireInput:
    """`form` — Flask `request.form` (или обычный dict с `.get()`, напр. в тестах)."""

    conveyor_kind = _enum_or_error(ConveyorKind, form.get("conveyor_kind"), "Вид конструкции",
                                    default=ConveyorKind.SHAFTED_TROUGH)

    abrasiveness_raw = form.get("abrasiveness") or ""
    abrasiveness = _enum_or_error(Abrasiveness, abrasiveness_raw, "Абразивность") if abrasiveness_raw else None

    material = MaterialInput(
        material_name=(form.get("material_name") or "").strip(),
        bulk_density_kg_m3=_float_or_none(form.get("bulk_density_kg_m3")),
        max_lump_size_mm=_float_or_none(form.get("max_lump_size_mm")),
        is_sorted_material=_checkbox(form, "is_sorted_material"),
        abrasiveness=abrasiveness,
        moisture_percent=_float_or_none(form.get("moisture_percent")),
        is_fibrous=_optional_bool(form, "is_fibrous"),
        is_sticky=_optional_bool(form, "is_sticky"),
        temperature_c=_float_or_none(form.get("temperature_c")),
    )

    # Исправлено 17.09.2026 (Issue #3): производительность больше НЕ обязательна на уровне формы —
    # для SHAFTED_TUBE она честно может быть неизвестна заказчику; validate_questionnaire() требует
    # её ТОЛЬКО для SHAFTED_TROUGH (там и остаётся понятная ошибка "Не указана требуемая
    # производительность", просто через общий путь валидации, а не здесь принудительно для всех видов).
    productivity_value = _float_or_none(form.get("productivity_value"))
    productivity_unit_raw = form.get("productivity_unit") or ""
    if productivity_value is not None:
        productivity_unit = _enum_or_error(ProductivityUnit, productivity_unit_raw, "Единица производительности",
                                            default=ProductivityUnit.T_H)
    else:
        productivity_unit = (
            _enum_or_error(ProductivityUnit, productivity_unit_raw, "Единица производительности")
            if productivity_unit_raw else None
        )
    productivity = ProductivityInput(value=productivity_value, unit=productivity_unit)

    geometry_mode = _enum_or_error(GeometryMode, form.get("geometry_mode"), "Способ задания геометрии",
                                    default=GeometryMode.AXIS_LENGTH_ANGLE)
    geometry_kwargs: dict[str, Any] = {"mode": geometry_mode}
    if geometry_mode == GeometryMode.AXIS_LENGTH_ANGLE:
        geometry_kwargs["working_length_mm"] = _float_or_none(form.get("working_length_mm"))
        incline = _float_or_none(form.get("incline_deg"))
        geometry_kwargs["incline_deg"] = incline if incline is not None else 0.0
    elif geometry_mode == GeometryMode.PROJECTION_HEIGHT:
        geometry_kwargs["horizontal_projection_mm"] = _float_or_none(form.get("horizontal_projection_mm"))
        geometry_kwargs["height_gain_mm"] = _float_or_none(form.get("height_gain_mm"))
    elif geometry_mode == GeometryMode.COORDINATES:
        def _xyz(prefix: str) -> tuple[float, float, float] | None:
            vals = [_float_or_none(form.get(f"{prefix}_{axis}_mm")) for axis in ("x", "y", "z")]
            if any(v is None for v in vals):
                return None
            return (vals[0], vals[1], vals[2])
        geometry_kwargs["load_point_xyz_mm"] = _xyz("load")
        geometry_kwargs["unload_point_xyz_mm"] = _xyz("unload")
    overall_length = _float_or_none(form.get("overall_length_mm"))
    if overall_length is not None:
        geometry_kwargs["overall_length_mm"] = overall_length
    # Поля SHAFTED_TUBE (Issue #3, добавлено 17.09.2026) — независимы от geometry_mode,
    # используются только для перекрёстной сверки core/tube_engineering.py::check_geometry_conflict();
    # для SHAFTED_TROUGH просто остаются None и ни на что не влияют.
    geometry_kwargs["connection_diameter_mm"] = _float_or_none(form.get("connection_diameter_mm"))
    geometry_kwargs["load_height_from_floor_mm"] = _float_or_none(form.get("load_height_from_floor_mm"))
    geometry_kwargs["unload_height_from_floor_mm"] = _float_or_none(form.get("unload_height_from_floor_mm"))
    geometry = GeometryInput(**geometry_kwargs)

    profile = OperatingProfileInput(
        duty_mode=(form.get("duty_mode") or "нормальный").strip(),
        environment=(form.get("environment") or "цех, без агрессивной среды").strip(),
        construction_material=(form.get("construction_material") or "Ст3").strip(),
    )

    # SHAFTED_TUBE (Issue #3, добавлено 17.09.2026) — до этой правки эти поля были
    # доступны только через прямой Python API (app.create_project), веб-форма их не
    # читала вообще. Все Optional — для SHAFTED_TROUGH просто останутся None.
    drive_location_text_raw = (form.get("drive_location_text") or "").strip()
    drive_location_graphic_raw = (form.get("drive_location_graphic") or "").strip()
    optional = OptionalDetails(
        startup_under_load=_optional_bool(form, "startup_under_load"),
        inlet_backpressure=_optional_bool(form, "inlet_backpressure"),
        reverse_required=_optional_bool(form, "reverse_required"),
        multiple_outlets=_optional_bool(form, "multiple_outlets"),
        washdown_required=_optional_bool(form, "washdown_required"),
        special_execution=(form.get("special_execution") or "").strip() or None,
        drive_power_supply=(form.get("drive_power_supply") or "").strip() or None,
        is_slurry_mixture=_optional_bool(form, "is_slurry_mixture"),
        solids_concentration_percent=_float_or_none(form.get("solids_concentration_percent")),
        duty_hours_per_day=_float_or_none(form.get("duty_hours_per_day")),
        starts_per_day=_int_or_none(form.get("starts_per_day")),
        corrosion_requirements=(form.get("corrosion_requirements") or "").strip() or None,
        drain_connection_required=_optional_bool(form, "drain_connection_required"),
        drive_location_text=(
            _enum_or_error(DriveLocation, drive_location_text_raw, "Расположение привода (текст)").value
            if drive_location_text_raw else None
        ),
        drive_location_text_source=(form.get("drive_location_text_source") or "").strip() or None,
        drive_location_graphic=(
            _enum_or_error(DriveLocation, drive_location_graphic_raw, "Расположение привода (графика)").value
            if drive_location_graphic_raw else None
        ),
        drive_location_graphic_source=(form.get("drive_location_graphic_source") or "").strip() or None,
    )

    return QuestionnaireInput(
        conveyor_kind=conveyor_kind, material=material, productivity=productivity,
        geometry=geometry, profile=profile, optional=optional,
        forced_diameter_mm=_float_or_none(form.get("forced_diameter_mm")),
        forced_step_mm=_float_or_none(form.get("forced_step_mm")),
    )


def form_defaults_from_questionnaire(q: QuestionnaireInput | None) -> dict[str, Any]:
    """Обратное преобразование — для предзаполнения формы редактирования существующего проекта."""
    if q is None:
        return {}
    d: dict[str, Any] = {
        "conveyor_kind": q.conveyor_kind.value,
        "material_name": q.material.material_name,
        "bulk_density_kg_m3": q.material.bulk_density_kg_m3,
        "max_lump_size_mm": q.material.max_lump_size_mm,
        "is_sorted_material": q.material.is_sorted_material,
        "abrasiveness": q.material.abrasiveness.value if q.material.abrasiveness else "",
        "moisture_percent": q.material.moisture_percent,
        "temperature_c": q.material.temperature_c,
        "productivity_value": q.productivity.value,
        "productivity_unit": q.productivity.unit.value if q.productivity.unit is not None else "",
        "geometry_mode": q.geometry.mode.value,
        "working_length_mm": q.geometry.working_length_mm,
        "incline_deg": q.geometry.incline_deg,
        "horizontal_projection_mm": q.geometry.horizontal_projection_mm,
        "height_gain_mm": q.geometry.height_gain_mm,
        "overall_length_mm": q.geometry.overall_length_mm,
        "duty_mode": q.profile.duty_mode,
        "environment": q.profile.environment,
        "construction_material": q.profile.construction_material,
        "startup_under_load": q.optional.startup_under_load,
        "inlet_backpressure": q.optional.inlet_backpressure,
        "reverse_required": q.optional.reverse_required,
        "multiple_outlets": q.optional.multiple_outlets,
        "washdown_required": q.optional.washdown_required,
        "special_execution": q.optional.special_execution or "",
        "drive_power_supply": q.optional.drive_power_supply or "",
        "forced_diameter_mm": q.forced_diameter_mm,
        "forced_step_mm": q.forced_step_mm,
        # SHAFTED_TUBE (Issue #3, 17.09.2026)
        "connection_diameter_mm": q.geometry.connection_diameter_mm,
        "load_height_from_floor_mm": q.geometry.load_height_from_floor_mm,
        "unload_height_from_floor_mm": q.geometry.unload_height_from_floor_mm,
        "is_slurry_mixture": q.optional.is_slurry_mixture,
        "solids_concentration_percent": q.optional.solids_concentration_percent,
        "duty_hours_per_day": q.optional.duty_hours_per_day,
        "starts_per_day": q.optional.starts_per_day,
        "corrosion_requirements": q.optional.corrosion_requirements or "",
        "drain_connection_required": q.optional.drain_connection_required,
        "drive_location_text": q.optional.drive_location_text or "",
        "drive_location_text_source": q.optional.drive_location_text_source or "",
        "drive_location_graphic": q.optional.drive_location_graphic or "",
        "drive_location_graphic_source": q.optional.drive_location_graphic_source or "",
    }
    if q.geometry.load_point_xyz_mm:
        d["load_x_mm"], d["load_y_mm"], d["load_z_mm"] = q.geometry.load_point_xyz_mm
    if q.geometry.unload_point_xyz_mm:
        d["unload_x_mm"], d["unload_y_mm"], d["unload_z_mm"] = q.geometry.unload_point_xyz_mm
    return d

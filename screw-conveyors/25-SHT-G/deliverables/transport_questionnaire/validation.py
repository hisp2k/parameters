"""Validation and JSON schema for the screw conveyor questionnaire.

This module collects design inputs. It does not perform strength calculations.
"""

from __future__ import annotations

from typing import Any
from purchased import cad_compatibility_warnings, validate_items
from material_catalog import get_card
from support_layout import body_support_layout


GOST_PITCHES_MM = {
    100: (80, 100),
    125: (100, 125),
    160: (125, 160),
    200: (160, 200),
    250: (200, 250),
    320: (250, 320),
    400: (320, 400),
    500: (400, 500),
}


def _number(value: Any, label: str, errors: list[str], *, minimum=None, maximum=None,
            integer=False, required=True):
    if value is None or str(value).strip() == "":
        if required:
            errors.append(f"{label}: заполните значение.")
        return None
    try:
        parsed = float(str(value).strip().replace(" ", "").replace(",", "."))
        if not (-float("inf") < parsed < float("inf")):
            raise ValueError
        if integer and not parsed.is_integer():
            raise ValueError
    except ValueError:
        errors.append(f"{label}: требуется {'целое' if integer else 'число'}.")
        return None
    if minimum is not None and parsed < minimum:
        errors.append(f"{label}: минимум {minimum}.")
    if maximum is not None and parsed > maximum:
        errors.append(f"{label}: максимум {maximum}.")
    return int(parsed) if integer else parsed


def _choice(value: Any, options: tuple[str, ...], label: str, errors: list[str]):
    if value not in options:
        errors.append(f"{label}: выберите {' / '.join(options)}.")
        return None
    return value


def _text(value: Any, label: str, errors: list[str], required=True):
    result = str(value or "").strip()
    if required and not result:
        errors.append(f"{label}: заполните значение.")
    return result


def _opening(row: dict, index: int, kind: str, length: float | None,
             errors: list[str]) -> dict:
    label = f"{'Загрузка' if kind == 'inlet' else 'Выгрузка'} {index}"
    x = _number(row.get("position_mm"), f"{label}, координата", errors, minimum=0)
    shape = _choice(row.get("shape"), ("round", "rectangular"), f"{label}, форма", errors)
    diameter = axial_length = width = None
    if shape == "round":
        diameter = _number(row.get("diameter_mm"), f"{label}, диаметр", errors, minimum=0.001)
        extent = diameter
    elif shape == "rectangular":
        axial_length = _number(row.get("length_mm"), f"{label}, длина", errors, minimum=0.001)
        width = _number(row.get("width_mm"), f"{label}, ширина", errors, minimum=0.001)
        extent = axial_length
    else:
        extent = None
    if x is not None and extent is not None and length is not None:
        if x - extent / 2 < 0 or x + extent / 2 > length:
            errors.append(f"{label}: отверстие выходит за рабочую длину желоба.")
    result = {
        "position_mm": x,
        "shape": shape,
        "diameter_mm": diameter,
        "length_mm": axial_length,
        "width_mm": width,
    }
    if kind == "outlet":
        direction = _choice(row.get("direction"), ("down", "side"), f"{label}, направление", errors)
        side = None
        if direction == "side":
            side = _choice(row.get("side"), ("left", "right"), f"{label}, сторона", errors)
        result.update(direction=direction, side=side)
    return result


def _flows(rows: list[dict], raw_rows: list[dict], simultaneous: Any,
           total_flow: float | None, kind: str, errors: list[str]) -> None:
    if len(rows) <= 1:
        if rows:
            rows[0]["flow_m3_h"] = total_flow
        return
    option = _choice(simultaneous, ("yes", "no"),
                     f"Одновременная работа точек {'загрузки' if kind == 'inlet' else 'выгрузки'}", errors)
    if option != "yes":
        for row in rows:
            row["flow_m3_h"] = None
        return
    values = []
    for index, (row, raw) in enumerate(zip(rows, raw_rows), 1):
        flow = _number(raw.get("flow_m3_h"), f"{'Загрузка' if kind == 'inlet' else 'Выгрузка'} {index}, расход",
                       errors, minimum=0)
        row["flow_m3_h"] = flow
        if flow is not None:
            values.append(flow)
    if total_flow is not None and len(values) == len(rows):
        tolerance = max(0.01, total_flow * 0.005)
        if abs(sum(values) - total_flow) > tolerance:
            errors.append(f"Сумма расходов по точкам {'загрузки' if kind == 'inlet' else 'выгрузки'} "
                          f"должна равняться общей производительности ({total_flow:g} м³/ч).")


def validate(raw: dict) -> tuple[dict, list[str], list[str]]:
    """Return (normalized inputs, errors, engineering warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    general = raw.get("general") or {}
    screw = raw.get("screw") or {}
    material = raw.get("material") or {}
    installation = raw.get("installation") or {}
    operation = raw.get("operation") or {}

    working_length = _number(general.get("working_length_mm"), "Рабочая длина", errors,
                             minimum=500, maximum=25000)
    angle = _number(general.get("inclination_deg"), "Угол наклона", errors,
                    minimum=0, maximum=20)
    throughput = _number(general.get("throughput_m3_h"), "Производительность", errors,
                         minimum=0.001)
    batch = _number(general.get("batch_volume_m3"), "Объём разовой загрузки", errors,
                    minimum=0.001)
    material_name = _text(material.get("name"), "Материал", errors)

    diameter_mode = _choice(screw.get("diameter_mode"), ("auto", "manual"),
                            "Диаметр шнека", errors)
    diameter = None
    if diameter_mode == "manual":
        diameter = _number(screw.get("diameter_mm"), "Диаметр шнека", errors,
                           minimum=50, maximum=600)
    pitch_mode = _choice(screw.get("pitch_mode"), ("gost", "manual"), "Шаг шнека", errors)
    pitch = None
    if pitch_mode == "manual":
        pitch = _number(screw.get("pitch_mm"), "Шаг шнека", errors, minimum=0.001)
    elif pitch_mode == "gost" and diameter_mode == "manual" and diameter is not None:
        available = GOST_PITCHES_MM.get(diameter)
        if available is None:
            errors.append("Для нестандартного диаметра укажите шаг вручную в миллиметрах.")
        else:
            pitch = _number(screw.get("pitch_mm"), "Шаг из пары ГОСТ", errors, minimum=0.001)
            if pitch is not None and pitch not in available:
                errors.append(f"Для D={diameter:g} мм допустимые шаги по таблице ГОСТ: "
                              + ", ".join(map(str, available)) + " мм.")
    if diameter is not None and diameter not in GOST_PITCHES_MM:
        warnings.append("Диаметр вне ряда ГОСТ 2037-82: исполнение нестандартное.")
    if pitch_mode == "manual":
        warnings.append("Шаг задан вручную: нормативность пары D/S и работа с материалом требуют проверки.")

    inlet_count = _number(raw.get("inlet_count"), "Количество загрузок", errors,
                          minimum=1, maximum=7, integer=True)
    outlet_count = _number(raw.get("outlet_count"), "Количество выгрузок", errors,
                           minimum=1, maximum=2, integer=True)
    raw_inlets = raw.get("inlets") or []
    raw_outlets = raw.get("outlets") or []
    if inlet_count is not None and len(raw_inlets) != inlet_count:
        errors.append("Число заполненных загрузок не совпадает с указанным количеством.")
    if outlet_count is not None and len(raw_outlets) != outlet_count:
        errors.append("Число заполненных выгрузок не совпадает с указанным количеством.")
    inlets = [_opening(row, i, "inlet", working_length, errors)
              for i, row in enumerate(raw_inlets, 1)]
    outlets = [_opening(row, i, "outlet", working_length, errors)
               for i, row in enumerate(raw_outlets, 1)]
    _flows(inlets, raw_inlets, raw.get("inlets_simultaneous"), throughput, "inlet", errors)
    _flows(outlets, raw_outlets, raw.get("outlets_simultaneous"), throughput, "outlet", errors)

    material_source = _choice(material.get("source"), ("manual", "catalog"),
                              "Источник свойств материала", errors)
    card_code = ""
    card = None
    density = lump = moisture = temperature = None
    abrasion = flowability = corrosion = None
    corrosion_note = ""
    if material_source == "catalog":
        card_code = _text(material.get("catalog_code"), "Код карточки материала", errors)
        if card_code:
            try:
                card = get_card(card_code)
                density = card["bulk_density_max_kg_m3"]
                lump = card["max_lump_mm"]
                if material_name and material_name != card["name"]:
                    errors.append("Название материала не совпадает с выбранной карточкой справочника.")
                warnings.append("Плотность из справочника следует подтвердить пробой материала перед выпуском проекта.")
            except ValueError as exc:
                errors.append(str(exc))
        moisture = _number(material.get("max_moisture_pct"), "Максимальная влажность", errors,
                           minimum=0, required=False)
        temperature = _number(material.get("temperature_c"), "Температура материала", errors,
                              required=False)
        if material.get("abrasion"):
            abrasion = _choice(material.get("abrasion"), ("low", "medium", "high"), "Абразивность", errors)
        if material.get("flowability"):
            flowability = _choice(material.get("flowability"), ("free", "sticky"), "Сыпучесть", errors)
        if material.get("corrosion"):
            corrosion = _choice(material.get("corrosion"), ("no", "yes"), "Коррозионность", errors)
        if corrosion == "yes":
            corrosion_note = _text(material.get("corrosion_note"), "Описание коррозионного воздействия", errors)
        if moisture is None or temperature is None or abrasion is None or flowability is None:
            warnings.append("Влажность, абразивность, сыпучесть и температуру нужно задать до подбора привода.")
        if moisture is not None and moisture > 0:
            warnings.append("Справочная насыпная плотность не подтверждена для указанной влажности; "
                            "для расчёта опор нужна плотность фактической влажной смеси.")
    elif material_source == "manual":
        density = _number(material.get("bulk_density_kg_m3"), "Насыпная плотность", errors, minimum=0.001)
        lump = _number(material.get("max_lump_mm"), "Максимальный размер куска", errors, minimum=0)
        moisture = _number(material.get("max_moisture_pct"), "Максимальная влажность", errors,
                           minimum=0)
        abrasion = _choice(material.get("abrasion"), ("low", "medium", "high"), "Абразивность", errors)
        flowability = _choice(material.get("flowability"), ("free", "sticky"), "Сыпучесть", errors)
        temperature = _number(material.get("temperature_c"), "Температура материала", errors)
        corrosion = _choice(material.get("corrosion"), ("no", "yes"), "Коррозионность", errors)
        if corrosion == "yes":
            corrosion_note = _text(material.get("corrosion_note"), "Описание коррозионного воздействия", errors)
        if corrosion == "yes":
            warnings.append("Агрессивная среда требует отдельного технического задания.")
    if density is not None and density > 2600:
        warnings.append("Плотность груза превышает область применения ГОСТ 2037-82; расчёт вести как нестандартное исполнение.")
    moisture_basis = None
    if moisture is not None and moisture > 0:
        moisture_basis = _choice(material.get("moisture_basis"), ("wet", "dry"),
                                 "База отсчёта влажности", errors)
        if moisture_basis == "wet" and moisture >= 100:
            errors.append("Влажность по массе влажной смеси должна быть меньше 100 %.")
    if lump is not None and lump > 20:
        warnings.append("Размер куска превышает область применения ГОСТ 2037-82.")
    if temperature is not None and temperature > 80:
        warnings.append("Температура материала превышает область применения ГОСТ 2037-82.")

    height_source = _choice(installation.get("height_source"), ("existing", "manual"),
                            "Высота оси у входа", errors)
    axis_height = None
    if height_source == "manual":
        axis_height = _number(installation.get("axis_height_mm"), "Высота оси у входа", errors,
                              minimum=0.001)
    elif height_source == "existing":
        warnings.append("Высоту оси нужно подтвердить обмером существующей установки.")
    supports_free = _choice(installation.get("supports_free"), ("yes", "no"),
                            "Свободное размещение опор корпуса", errors)
    support_note = ""
    if supports_free == "no":
        support_note = _text(installation.get("support_positions"), "Разрешённые места опор", errors)
    environment = _choice(installation.get("environment"), ("inside", "outside"),
                          "Размещение", errors)
    site = ""
    if environment == "outside":
        site = _text(installation.get("site_location"), "Местоположение площадки", errors)

    duty = _choice(operation.get("duty"), ("continuous", "intermittent"), "Режим работы", errors)
    hours = _number(operation.get("hours_per_day"), "Часов работы в сутки", errors,
                    minimum=0.001, maximum=24)
    starts = _number(operation.get("starts_per_hour"), "Пусков в час", errors,
                     minimum=0, integer=True)
    loaded_start = _choice(operation.get("loaded_start"), ("yes", "no"),
                           "Пуск с заполненным желобом", errors)
    reverse = _choice(operation.get("reverse"), ("yes", "no"), "Реверс", errors)
    blockage = _choice(operation.get("blockage"), ("yes", "no"), "Возможность закупорки", errors)
    protection = None
    if blockage == "yes":
        protection = _choice(operation.get("overload_protection"), ("yes", "no"),
                             "Защита от перегрузки", errors)
    hopper = _choice(operation.get("hopper"), ("yes", "no"), "Загрузка из бункера", errors)
    head = None
    if hopper == "yes":
        head = _number(operation.get("hopper_head_mm"), "Высота столба материала", errors,
                       minimum=0.001)
    life = _number(operation.get("design_life_h"), "Требуемый ресурс", errors, minimum=0.001)

    normalized = {
        "general": {
            "working_length_mm": working_length,
            "inclination_deg": angle,
            "throughput_m3_h": throughput,
            "batch_volume_m3": batch,
        },
        "screw": {
            "diameter_mode": diameter_mode,
            "diameter_mm": diameter,
            "pitch_mode": pitch_mode,
            "pitch_mm": pitch,
        },
        "inlets": inlets,
        "inlets_simultaneous": raw.get("inlets_simultaneous") if len(inlets) > 1 else None,
        "outlets": outlets,
        "outlets_simultaneous": raw.get("outlets_simultaneous") if len(outlets) > 1 else None,
        "material": {
            "name": material_name,
            "source": material_source,
            "catalog_code": card_code,
            "bulk_density_kg_m3": density,
            "max_lump_mm": lump,
            "max_moisture_pct": moisture,
            "moisture_basis": moisture_basis,
            "abrasion": abrasion,
            "flowability": flowability,
            "temperature_c": temperature,
            "corrosion": corrosion,
            "corrosion_note": corrosion_note,
            "reference_url": card["source_url"] if card else None,
            "density_status": ("requires_wet_material_confirmation" if card and moisture is not None
                               and moisture > 0 else "reference" if card else "entered_by_user"),
        },
        "installation": {
            "height_source": height_source,
            "axis_height_mm": axis_height,
            "supports_free": supports_free,
            "support_positions": support_note,
            "environment": environment,
            "site_location": site,
            "special_requirements": str(installation.get("special_requirements") or "").strip(),
        },
        "operation": {
            "duty": duty,
            "hours_per_day": hours,
            "starts_per_hour": starts,
            "loaded_start": loaded_start,
            "reverse": reverse,
            "blockage": blockage,
            "overload_protection": protection,
            "hopper": hopper,
            "hopper_head_mm": head,
            "design_life_h": life,
        },
        # Optional Simulation inputs are checked by the strength block itself.
        "strength": {key: str((raw.get("strength") or {}).get(key)
                              if (raw.get("strength") or {}).get(key) is not None else "").strip() for key in
                     ("torque_nm", "axial_force_n", "simulation_material", "yield_strength_mpa",
                      "required_safety_factor", "mesh_size_mm")},
    }
    if working_length is not None:
        normalized["body_support_layout"] = body_support_layout(working_length)
    if "purchased_items" in raw:
        try:
            normalized["purchased_items"] = validate_items(raw["purchased_items"])
            warnings.extend(cad_compatibility_warnings(normalized["purchased_items"]))
        except ValueError as exc:
            errors.append(f"Покупные изделия: {exc}")
    return normalized, errors, warnings

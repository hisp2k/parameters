"""Normative checks and traceable calculations for the shafted screw.

No unverified transport-efficiency or motor-power coefficients are assumed.
"""
from __future__ import annotations

import math

from bulk_materials import MATERIALS, catalog as material_catalog

GOST_URL = "https://files.stroyinf.ru/Data2/1/4294751/4294751811.pdf"
RPM_SERIES = (6, 7.5, 9.5, 11.8, 15, 19, 23.6, 30, 37.5, 47.5, 60, 75, 95, 118, 150, 190)
STANDARD_PAIRS = {
    100: (80, 100), 125: (100, 125), 160: (125, 160), 200: (160, 200),
    250: (200, 250), 320: (250, 320), 400: (320, 400), 500: (400, 500),
    650: (500, 650), 800: (650, 800),
}
CAPACITY_SERIES = (0.025, 0.032, 0.04, 0.05, 0.063, 0.08, 0.1, 0.125, 0.16,
                   0.25, 0.32, 0.4, 0.5, 0.63, 0.8, 1, 1.25, 1.6, 2.5,
                   3.2, 4, 5, 6.3, 8, 10, 12.5, 16, 25, 32, 40, 50,
                   63, 80, 100, 125, 160, 250, 400, 500)
INPUTS = ("rpm", "target_m3_h", "bulk_density_kg_m3", "lump_mm", "cargo_temp_c", "material_key",
          "measured_mass_kg", "measured_time_s")

def _number(raw, name, *, positive=True):
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{name}: требуется число")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: требуется число") from exc
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name}: требуется конечное значение больше нуля")
    return value

def _check(key, status, actual, requirement, clause):
    return {"id": key, "status": status, "actual": actual,
            "requirement": requirement, "source": "ГОСТ 2037-82, " + clause}

def calculate(values: dict, raw_inputs: dict | None = None) -> dict:
    from bridge import validate  # reuse the CAD geometry validation
    errors = validate(values)
    if errors:
        raise ValueError("; ".join(errors))
    raw_inputs = raw_inputs or {}
    if not isinstance(raw_inputs, dict) or set(raw_inputs) - set(INPUTS):
        raise ValueError("Неизвестные входные данные расчёта")
    inp = {key: _number(raw_inputs.get(key), key, positive=key != "cargo_temp_c")
           for key in INPUTS if key != "material_key"}
    material_key = raw_inputs.get("material_key") or None
    if material_key is not None and material_key not in MATERIALS:
        raise ValueError("Неизвестный справочный груз")
    inp["material_key"] = material_key
    d = values["screw_diameter"]
    pitch = values["pitch"]
    bore = values["tube_diameter"] - 2 * values["tube_wall"]
    gap = (bore - d) / 2
    annulus = math.pi / 4 * (d * d - values["shaft_diameter"] ** 2) / 1_000_000
    rev_volume = annulus * pitch / 1000
    checks = [
        _check("incline", "PASS" if 0 <= values["incline"] <= 20 else "BLOCK",
               values["incline"], "0–20° для наклонного конвейера", "п. 1.1"),
        _check("screw_pair", "PASS" if pitch in STANDARD_PAIRS.get(d, ()) else "BLOCK",
               f"Ø{d:g} / {pitch:g} мм", "пара диаметр–шаг из таблицы 1", "п. 2.1"),
        _check("radial_clearance", "PASS" if 8 <= gap <= 10 else "BLOCK",
               round(gap, 4), "номинальный зазор 8–10 мм", "п. 3.5"),
        _check("rpm", "REQUIRED" if inp["rpm"] is None else
               "PASS" if inp["rpm"] in RPM_SERIES else "BLOCK",
               inp["rpm"], "частота из ряда ГОСТ", "п. 2.2"),
        _check("bulk_density", "REQUIRED" if inp["bulk_density_kg_m3"] is None else
               "PASS" if inp["bulk_density_kg_m3"] <= 2600 else "BLOCK",
               inp["bulk_density_kg_m3"], "насыпная плотность ≤2600 кг/м³", "область применения"),
        _check("lump_size", "REQUIRED" if inp["lump_mm"] is None else
               "PASS" if inp["lump_mm"] <= 20 else "BLOCK",
               inp["lump_mm"], "размер куска ≤20 мм", "область применения"),
        _check("cargo_temperature", "REQUIRED" if inp["cargo_temp_c"] is None else
               "PASS" if inp["cargo_temp_c"] <= 80 else "BLOCK",
               inp["cargo_temp_c"], "температура груза ≤80 °C", "область применения"),
    ]
    results = {
        "bore_mm": round(bore, 4),
        "radial_clearance_mm": round(gap, 4),
        "working_length_mm": values["working_length"],
        "full_length_mm": values["working_length"] + 270,
        "annular_area_m2": round(annulus, 8),
        "geometric_volume_per_rev_m3": round(rev_volume, 9),
        "geometric_volume_per_hour_m3": None,
        "minimum_ideal_rpm_for_target": None,
        "required_effective_fraction": None,
        "requested_standard_capacity_m3_h": None,
        "measured_mass_flow_kg_h": None,
        "measured_volume_flow_m3_h": None,
        "reference_density_range_kg_m3": None,
        "reference_particle_limit_mm": None,
        "reference_particle_spec": None,
        "reference_vertical_candidate": None,
    }
    if material_key is not None:
        material = next(x for x in material_catalog()["items"] if x["id"] == material_key)
        results["reference_density_range_kg_m3"] = material["density_kg_m3"]
        results["reference_particle_limit_mm"] = material["max_particle_mm"]
        results["reference_particle_spec"] = material["particle_spec"]
        results["reference_vertical_candidate"] = material["vertical_candidate"]
    if inp["rpm"] is not None:
        results["geometric_volume_per_hour_m3"] = round(rev_volume * inp["rpm"] * 60, 5)
    target = inp["target_m3_h"]
    if target is not None:
        results["minimum_ideal_rpm_for_target"] = round(target / (rev_volume * 60), 3)
        selected = next((x for x in CAPACITY_SERIES if x >= target), None)
        results["requested_standard_capacity_m3_h"] = selected
        checks.append(_check("capacity_series", "PASS" if selected is not None else "BLOCK",
                             target, "ближайшее не меньшее значение из ряда (без подтверждения фактической подачи)", "п. 2.3"))
        if inp["rpm"] is not None:
            ideal = rev_volume * inp["rpm"] * 60
            fraction = target / ideal
            results["required_effective_fraction"] = round(fraction, 5)
            checks.append({
                "id": "target_geometry_bound",
                "status": "BLOCK" if fraction > 1 else "REQUIRED",
                "actual": round(fraction, 5),
                "requirement": f"доля фактической подачи от геометрического предела ≤1; подачу ≥{target:g} м³/ч подтвердить испытанием с данным грузом",
                "source": "геометрическая верхняя граница, не норматив ГОСТ",
            })
    mass, seconds = inp["measured_mass_kg"], inp["measured_time_s"]
    if mass is not None or seconds is not None:
        if mass is None or seconds is None:
            checks.append(_check("bench_measurement", "REQUIRED", None,
                                 "масса и время контрольного отрезка", "п. 7.4"))
        else:
            kg_h = mass * 3600 / seconds
            results["measured_mass_flow_kg_h"] = round(kg_h, 4)
            if inp["bulk_density_kg_m3"] is not None:
                results["measured_volume_flow_m3_h"] = round(kg_h / inp["bulk_density_kg_m3"], 5)
            checks.append(_check("bench_measurement", "PASS", round(kg_h, 4),
                                 "подача по измеренной массе за время; объёмная подача требует плотности", "п. 7.4"))
            if target is not None:
                actual_volume = results["measured_volume_flow_m3_h"]
                checks.append(_check("target_verification", "REQUIRED" if actual_volume is None else
                                     "PASS" if actual_volume >= target else "BLOCK",
                                     actual_volume, f"измеренная подача ≥{target:g} м³/ч", "п. 7.4"))
    summary = "BLOCK" if any(c["status"] == "BLOCK" for c in checks) else (
        "REQUIRED" if any(c["status"] == "REQUIRED" for c in checks) else "PARTIAL")
    return {"status": summary, "standard": "ГОСТ 2037-82", "standard_url": GOST_URL,
            "inputs": inp, "results": results, "checks": checks,
            "limitations": [
                "Геометрический объём не является прогнозом фактической производительности.",
                "Соответствие всего конвейера ГОСТ не устанавливается без проверки остальных требований и испытаний.",
                "Мощность, крутящий момент и прочность не рассчитываются без проверенной методики и исходных данных.",
            ]}

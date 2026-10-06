"""Documented load cases and bearing layout for the next design stage.

This module does not infer forces from throughput and does not run FEA.
It produces a versioned load-basis record tied to the supplied CAD files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import uuid
from datetime import datetime
from pathlib import Path

from cad_bridge import default_model_dir, prepare


REQUIRED_KEYS = (
    "motor_power_kw", "output_speed_rpm", "torque_limit_nm", "drive_spec_confirmed",
    "normal_axial_n", "normal_radial_n", "start_factor", "start_axial_n",
    "start_radial_n", "support_a_mm", "support_b_mm", "locating_support",
    "support_source",
)
OPTIONAL_CASE_KEYS = (
    "jam_axial_n", "jam_radial_n", "reverse_torque_nm", "reverse_axial_n",
    "reverse_radial_n",
)


def _number(value, label: str, *, positive=False, nonnegative=False) -> float:
    try:
        number = float(str(value).strip().replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{label}: введите число") from None
    if not math.isfinite(number):
        raise ValueError(f"{label}: требуется конечное число")
    if positive and number <= 0:
        raise ValueError(f"{label}: требуется значение больше нуля")
    if nonnegative and number < 0:
        raise ValueError(f"{label}: требуется значение не меньше нуля")
    return number


def _hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_cases(raw: dict, model_dir: str | Path) -> dict:
    """Validate load basis and derive distinct design cases without CAD edits."""
    cad = prepare(raw, model_dir)
    basis = raw.get("load_basis") or {}
    missing = [key for key in REQUIRED_KEYS if basis.get(key) is None or str(basis.get(key)).strip() == ""]
    operation = cad["inputs"]["operation"]
    if operation["blockage"] == "yes":
        missing += [key for key in ("jam_axial_n", "jam_radial_n")
                    if basis.get(key) is None or str(basis.get(key)).strip() == ""]
    if operation["reverse"] == "yes":
        missing += [key for key in ("reverse_torque_nm", "reverse_axial_n", "reverse_radial_n")
                    if basis.get(key) is None or str(basis.get(key)).strip() == ""]
    if missing:
        raise ValueError("Заполните расчётный паспорт: " + ", ".join(missing))
    if basis["drive_spec_confirmed"] != "yes":
        raise ValueError("Подтвердите характеристики установленного мотор-редуктора")
    if basis["locating_support"] not in ("A", "B"):
        raise ValueError("Укажите осевую фиксирующую опору: A или B")
    source = str(basis["support_source"]).strip()
    if not source:
        raise ValueError("Укажите источник схемы опирания")

    p_kw = _number(basis["motor_power_kw"], "Мощность двигателя, кВт", positive=True)
    rpm = _number(basis["output_speed_rpm"], "Частота на выходе редуктора, об/мин", positive=True)
    torque_limit = _number(basis["torque_limit_nm"], "Предельный передаваемый момент, Н·м", positive=True)
    # Exact conversion: T = P / omega, with P in kW and n in revolutions/minute.
    nominal_torque = 60000 * p_kw / (2 * math.pi * rpm)
    if torque_limit < nominal_torque:
        raise ValueError("Предельный момент ниже номинального момента P/ω")
    start_factor = _number(basis["start_factor"], "Коэффициент пускового момента", positive=True)
    if start_factor < 1:
        raise ValueError("Коэффициент пускового момента должен быть не менее 1")
    support_a = _number(basis["support_a_mm"], "Координата опоры A, мм")
    support_b = _number(basis["support_b_mm"], "Координата опоры B, мм")
    if abs(support_b - support_a) < 1:
        raise ValueError("Центры опор A и B должны различаться минимум на 1 мм")

    def axial(key, label):
        return _number(basis[key], label)

    def radial(key, label):
        return _number(basis[key], label, nonnegative=True)

    cases = [
        {"id": "normal", "name": "Нормальная работа", "torque_nm": nominal_torque,
         "axial_n": axial("normal_axial_n", "Осевая сила в работе"),
         "radial_n": radial("normal_radial_n", "Радиальная сила в работе")},
        {"id": "start", "name": "Пуск с грузом", "torque_nm": nominal_torque * start_factor,
         "axial_n": axial("start_axial_n", "Осевая сила при пуске"),
         "radial_n": radial("start_radial_n", "Радиальная сила при пуске")},
    ]
    if operation["blockage"] == "yes":
        cases.append({"id": "jam", "name": "Закупорка до срабатывания защиты",
                      "torque_nm": torque_limit,
                      "axial_n": axial("jam_axial_n", "Осевая сила при закупорке"),
                      "radial_n": radial("jam_radial_n", "Радиальная сила при закупорке")})
    if operation["reverse"] == "yes":
        cases.append({"id": "reverse", "name": "Реверс", "torque_nm":
                      -_number(basis["reverse_torque_nm"], "Момент при реверсе", positive=True),
                      "axial_n": axial("reverse_axial_n", "Осевая сила при реверсе"),
                      "radial_n": radial("reverse_radial_n", "Радиальная сила при реверсе")})
    if nominal_torque * start_factor > torque_limit:
        raise ValueError("Пусковой момент больше указанного предельного момента защиты; уточните защиту или пуск")

    for case in cases:
        case["axial_direction"] = "по оси от привода к выгрузке" if case["axial_n"] >= 0 else "против оси от привода к выгрузке"
        case["radial_direction_status"] = "не задана — для FEA нужна ориентация в плоскости сечения"
        case["source"] = str(basis.get(case["id"] + "_source") or "").strip()
        if not case["source"]:
            raise ValueError(f"Укажите источник нагрузок для случая «{case['name']}»")

    return {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "load_cases_defined_not_verified",
        "assembly": cad["assembly"],
        "screw_part": cad["part"],
        "model_sha256": {"assembly": _hash(cad["assembly"]), "screw": _hash(cad["part"])},
        "model_geometry_not_linked": cad["not_applied_to_geometry"],
        "model_compatibility_blocks": cad["blocked"],
        "input_warnings": cad["engineering_warnings"],
        "questionnaire_inputs": cad["inputs"],
        "drive": {"motor_power_kw": p_kw, "output_speed_rpm": rpm,
                  "nominal_torque_nm": nominal_torque, "torque_limit_nm": torque_limit,
                  "start_factor": start_factor, "source": str(basis.get("drive_source") or "").strip()},
        "supports": {"A_center_from_trough_start_mm": support_a,
                     "B_center_from_trough_start_mm": support_b,
                     "axially_locating": basis["locating_support"],
                     "source": source,
                     "CAD_faces_mapped": False},
        "cases": cases,
        "simulation_ready": False,
        "remaining_for_fea": ["привязать подшипники к поверхностям CAD и задать их жёсткости",
                              "задать направление радиальных сил",
                              "подтвердить нагрузки и источники", "параметризовать сборку по длине и диаметру"],
    }


def save_cases(plan: dict, model_dir: str | Path) -> Path:
    root = Path(model_dir).resolve()
    stem = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    path = root / f"РАСЧЁТНЫЕ_СЛУЧАИ_{stem}.json"
    with path.open("x", encoding="utf-8") as file:
        json.dump(plan, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Сформировать расчётные случаи и схему опирания")
    parser.add_argument("input", type=Path)
    parser.add_argument("--model", type=Path, default=default_model_dir())
    parser.add_argument("--check", action="store_true", help="Проверка без записи отчёта")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        plan = prepare_cases(payload.get("inputs", payload), args.model)
        if not args.check:
            plan["report_path"] = str(save_cases(plan, args.model))
    except Exception as exc:
        parser.exit(1, f"Ошибка: {exc}\n")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

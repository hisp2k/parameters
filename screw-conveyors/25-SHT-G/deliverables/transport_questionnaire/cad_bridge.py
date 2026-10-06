"""Apply a validated questionnaire to the supported SolidWorks geometry.

At present only the screw pitch of the supplied D=200 mm assembly is driven.
All other questionnaire values are recorded in an explicit link report.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from validation import validate


PART_GLOB = "*02.00.00.01*Шнек*SLDPRT"
ASSEMBLY_GLOB = "*00.00.00.00*Транспортер*SLDASM"
NOMINAL_DIAMETER_MM = 200.0


def default_model_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "25.SHT.G_parameterized"


def _validate_input(raw: dict) -> tuple[dict, list[str]]:
    if "inlet_count" not in raw:
        raw = {**raw, "inlet_count": len(raw.get("inlets", [])),
               "outlet_count": len(raw.get("outlets", []))}
    normalized, errors, warnings = validate(raw)
    if errors:
        raise ValueError("Опросный лист содержит ошибки:\n" + "\n".join(errors))
    return normalized, warnings


def prepare(raw: dict, model_dir: str | Path) -> dict:
    """Check compatibility without loading or changing SolidWorks documents."""
    data, warnings = _validate_input(raw)
    root = Path(model_dir).resolve()
    if root.name != "25.SHT.G_parameterized":
        raise ValueError("Для изменения выберите папку копии 25.SHT.G_parameterized")
    # SolidWorks leaves temporary lock files prefixed with ~$ while a document is open.
    parts = [p for p in root.glob(PART_GLOB) if not p.name.startswith("~$")]
    assemblies = [p for p in root.glob(ASSEMBLY_GLOB) if not p.name.startswith("~$")]
    if len(parts) != 1 or len(assemblies) != 1:
        raise FileNotFoundError("В папке модели должны быть одна деталь шнека и одна главная сборка")

    screw = data["screw"]
    diameter = screw["diameter_mm"]
    pitch = screw["pitch_mm"]
    blocks = []
    if diameter is None:
        blocks.append("Диаметр задан для автоматического подбора; расчёт подбора не подключён")
    elif not math.isclose(diameter, NOMINAL_DIAMETER_MM, abs_tol=1e-6):
        blocks.append(f"Сборка рассчитана на D={NOMINAL_DIAMETER_MM:g} мм; D={diameter:g} мм не связан с желобом, опорами и приводом")
    if pitch is None:
        blocks.append("Шаг не задан числом; для этой модели укажите шаг в мм")

    return {
        "model_dir": str(root), "part": str(parts[0]), "assembly": str(assemblies[0]),
        "inputs": data, "engineering_warnings": warnings, "blocked": blocks,
        "pitch_mm": pitch,
        "not_applied_to_geometry": [
            "длина рабочей части желоба", "угол наклона", "наружный диаметр шнека",
            "число, форма, размеры и положение загрузок", "число, форма, размеры и положение выгрузок",
            "высота и расположение опор", "привод и эксплуатационные нагрузки",
        ],
    }


def _dimension_mm(model, feature_name: str, dimension_name: str) -> float:
    feature = model.FirstFeature
    while feature:
        if feature.Name == feature_name:
            display = feature.GetFirstDisplayDimension
            while display:
                dimension = display.GetDimension2(0)
                if dimension.FullName.startswith(f"{dimension_name}@{feature_name}@"):
                    return dimension.SystemValue * 1000
                display = feature.GetNextDisplayDimension(display)
        feature = feature.GetNextFeature
    raise RuntimeError(f"Размер {dimension_name}@{feature_name} не найден в детали")


def _set_solidworks_pitch(part: str, pitch_mm: float) -> dict:
    # Import only during CAD application so preview and validation work without pywin32.
    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    sw = win32.Dispatch("SldWorks.Application")
    already_open = sw.GetOpenDocumentByName(part)
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model = sw.OpenDoc6(part, 1, 1, "", errors, warnings)
    if not model:
        raise RuntimeError(f"SolidWorks не открыл деталь шнека (код {errors.value})")
    title = model.GetTitle
    changed = False
    previous = None
    try:
        sw.ActivateDoc2(title, False, errors)
        if not math.isclose(_dimension_mm(model, "FLIGHT_SECTION", "D2"), NOMINAL_DIAMETER_MM, abs_tol=1e-5):
            raise RuntimeError("Фактический диаметр детали не равен 200 мм; изменение шага отменено")
        equations = model.GetEquationMgr
        index = next((i for i in range(equations.GetCount)
                      if equations.Equation(i).lstrip().startswith('"SCREW_PITCH"')), None)
        if index is None:
            raise RuntimeError("Переменная SCREW_PITCH отсутствует в детали")
        previous = equations.Equation(index)
        before = _dimension_mm(model, "HELIX_MASTER", "D4")
        if not math.isclose(before, pitch_mm, abs_tol=1e-6):
            equations.Equation(index, f'"SCREW_PITCH" = {pitch_mm:.10g}')
            changed = True
            if not model.EditRebuild3:
                raise RuntimeError("SolidWorks не перестроил шнек")
        actual = _dimension_mm(model, "HELIX_MASTER", "D4")
        if not math.isclose(actual, pitch_mm, abs_tol=1e-5):
            raise RuntimeError(f"Контроль шага не пройден: {actual:g} мм")
        if changed and not model.Save3(1, errors, warnings):
            raise RuntimeError(f"SolidWorks не сохранил шнек (код {errors.value})")
        return {"before_mm": before, "actual_mm": actual, "changed": changed,
                "solidworks_save_warnings": warnings.value}
    except Exception:
        if changed and previous is not None:
            try:
                equations.Equation(index, previous)
                model.EditRebuild3
            except Exception:
                pass
        raise
    finally:
        if not already_open:
            sw.CloseDoc(title)
        pythoncom.CoUninitialize()


def apply_to_model(plan: dict, *, dry_run: bool = False) -> dict:
    if plan["blocked"]:
        raise ValueError("Передача в CAD невозможна:\n" + "\n".join(plan["blocked"]))
    result = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "preview" if dry_run else "partial_geometry_applied",
        "model_assembly": plan["assembly"], "model_part": plan["part"],
        "questionnaire_inputs": plan["inputs"],
        "applied_geometry": {"screw_pitch_mm": plan["pitch_mm"]},
        "not_applied_to_geometry": plan["not_applied_to_geometry"],
        "engineering_warnings": plan["engineering_warnings"],
        "note": "Изменён только шаг шнека D=200 мм. Сборка в целом и прочность не проверены.",
    }
    if not dry_run:
        result["solidworks_verification"] = _set_solidworks_pitch(plan["part"], plan["pitch_mm"])
        report = Path(plan["model_dir"]) / "СВЯЗЬ_С_ОПРОСНЫМ_ЛИСТОМ.json"
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report_path"] = str(report)
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Передать проверенный опросный лист в копию модели SolidWorks")
    parser.add_argument("input", type=Path, help="JSON опросного листа")
    parser.add_argument("--model", type=Path, default=default_model_dir(), help="Папка копии CAD")
    parser.add_argument("--dry-run", action="store_true", help="Только проверить возможность передачи")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        plan = prepare(payload.get("inputs", payload), args.model)
        result = apply_to_model(plan, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Ошибка: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

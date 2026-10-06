"""SolidWorks bridge for the supplied shafted screw model."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

import pythoncom
import win32com.client as win32
from standards import validate_selection

BASE = Path(__file__).resolve().parent
CAD = BASE / "CAD"
RECOVERED_CAD = BASE / "CAD_восстановленный"
STATE = BASE / "state.json"
TOP_ASSEMBLY = RECOVERED_CAD / "PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"

FILES = {
    "tube": RECOVERED_CAD / "Труба в сборе — исправлено 20261004" / "PT.SHT.01.21.00.00 СБ 'Труба в сборе' — исправлено.SLDASM",
    "screw": RECOVERED_CAD / "Шнековый вал — исправлено 20261004" / "PT.SHT.01.24.00.00 СБ 'Шнековый вал' — исправлено.SLDASM",
    "support": RECOVERED_CAD / "Опора — исправлено 20261004" / "PT.SHT.01.25.00.00 СБ 'Опора шнековая' — исправлено.SLDASM",
}

SUPPORT_DIR = RECOVERED_CAD / "Опора — исправлено 20261004"
PART_FIELDS = {
    "support_short_beam_length": (SUPPORT_DIR / "PT.SHT.01.25.00.01 'Балка 1'_SPCR04_SPR04.SLDPRT",
                                  ("D1@Бобышка-Вытянуть1", "D2@Бобышка-Вытянуть1")),
    "support_long_beam_length": (SUPPORT_DIR / "PT.SHT.01.25.00.03 'Балка 2'_SPCR04_SPR04.SLDPRT",
                                 ("D1@Бобышка-Вытянуть1", "D2@Бобышка-Вытянуть1")),
}

FIELDS = {
    "working_length": [("tube", "Длина трубы"), ("screw", "Длина вала")],
    "tube_diameter": [("tube", "Диаметр трубы")],
    "tube_wall": [("tube", "Толщина стенки трубы")],
    "incline": [("tube", "Угол наклона")],
    "inlet_diameter": [("tube", "Диаметр патрубка")],
    "inlet_length": [("tube", "Длина патрубка")],
    "inlet_wall": [("tube", "Толщина стенки патрубка")],
    "flange_thickness": [("tube", "Толщина фланца")],
    "mounting_hole_diameter": [("tube", "Отверстие М8")],
    "discharger_diameter": [("tube", "Диаметр сбрасывателя")],
    "discharger_length": [("tube", "Длина сбрасывателя")],
    "screw_diameter": [("screw", "Диаметр винта шнека")],
    "pitch": [("screw", "Шаг винта шнека")],
    "blade_thickness": [("screw", "Толщина лопасти")],
    "shaft_diameter": [("screw", "Диаметр вала шнека")],
    "shaft_wall": [("screw", "Толщина стенки вала")],
    "turns": [("screw", "Число витков")],
}

def validate(values: dict) -> list[str]:
    errors = []
    if set(values) != set(FIELDS) | set(PART_FIELDS):
        return ["Набор параметров не соответствует модели."]
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{key}: требуется конечное число")
        elif value < 0 or (key != "incline" and value == 0):
            errors.append(f"{key}: значение должно быть {'неотрицательным' if key == 'incline' else 'больше нуля'}")
    if errors:
        return errors
    if values["incline"] >= 90:
        errors.append("Угол наклона должен быть меньше 90°.")
    if values["tube_diameter"] - 2 * values["tube_wall"] <= values["screw_diameter"]:
        errors.append("Внутренний диаметр трубы должен быть больше диаметра винта.")
    if values["tube_diameter"] <= 2 * values["tube_wall"]:
        errors.append("Толщина стенки трубы не оставляет проходного сечения.")
    if values["screw_diameter"] <= values["shaft_diameter"]:
        errors.append("Диаметр винта должен быть больше диаметра вала.")
    if values["shaft_diameter"] <= 2 * values["shaft_wall"]:
        errors.append("Толщина стенки вала не оставляет внутреннего сечения.")
    if values["inlet_diameter"] <= 2 * values["inlet_wall"]:
        errors.append("Толщина стенки патрубка не оставляет проходного сечения.")
    if values["pitch"] * values["turns"] + 2 * values["blade_thickness"] > values["working_length"] + 85:
        errors.append("Винтовая часть с торцевой деталью заходит в верхнюю ступень вала: шаг × число витков + две толщины лопасти должны быть не больше рабочей длины + 85 мм для этой модели.")
    if int(values["turns"]) != values["turns"]:
        errors.append("Число витков должно быть целым.")
    return errors

def equation_for(name: str, key: str, value: float) -> str:
    if key == "working_length":
        return f'"{name}"= {value:g}мм + 270'
    if key == "turns":
        return f'"{name}"= {int(value)}'
    unit = "градусов" if key == "incline" else "мм"
    return f'"{name}"= {value:g}{unit}'

def open_models(sw):
    top = sw.GetOpenDocumentByName(str(TOP_ASSEMBLY))
    if top is None:
        spec = sw.GetOpenDocSpec(str(TOP_ASSEMBLY))
        spec.DocumentType = 2
        spec.Silent = True
        top = sw.OpenDoc7(spec)
    if top is None or bool(top.IsOpenedReadOnly):
        raise RuntimeError("Рабочую сборку не удалось открыть для изменения.")
    linked = {Path(c.GetPathName).resolve() for c in top.GetComponents(True) or [] if c.GetPathName}
    disconnected = [p.name for p in FILES.values() if p.resolve() not in linked]
    if disconnected:
        raise RuntimeError("Программа ссылается на узлы вне рабочей сборки: " + ", ".join(disconnected))
    docs = {}
    for key, path in FILES.items():
        if not path.is_file():
            raise RuntimeError(f"Отсутствует CAD-файл: {path}")
        doc = next((d for d in (sw.GetDocuments or []) if d.GetPathName.lower() == str(path).lower()), None)
        if doc is None:
            spec = sw.GetOpenDocSpec(str(path))
            spec.DocumentType = 2
            spec.Silent = True
            spec.ReadOnly = False
            doc = sw.OpenDoc7(spec)
        if doc is None or doc.GetPathName.lower() != str(path).lower():
            raise RuntimeError(f"Не удалось открыть копию {path.name} для записи.")
        if bool(doc.IsOpenedReadOnly):
            raise RuntimeError(f"Файл {path.name} открыт только для чтения. Закройте его в SolidWorks и повторите действие.")
        docs[key] = doc
    return docs

def globals_in(doc):
    mgr = doc.GetEquationMgr
    result = {}
    for i in range(mgr.GetCount):
        expression = mgr.Equation(i)
        match = re.match(r'^\s*"([^"]+)"\s*=', expression)
        if match and "@" not in match.group(1):
            result[match.group(1)] = (i, expression)
    return mgr, result

def set_equation(mgr, index: int, expression: str):
    mgr._oleobj_.InvokeTypes(
        8, 0, pythoncom.DISPATCH_PROPERTYPUT,
        (pythoncom.VT_EMPTY, 0),
        ((pythoncom.VT_I4, 1), (pythoncom.VT_BSTR, 1)),
        index, expression,
    )
    if mgr.Equation(index) != expression:
        raise RuntimeError(f"SolidWorks не принял уравнение {expression}")

def validate_design_mode(values: dict, mode: str) -> list[str]:
    if mode not in ("gost", "special"):
        return ["Неизвестный режим угла наклона."]
    angle = values.get("incline")
    if mode == "gost" and isinstance(angle, (int, float)) and not isinstance(angle, bool) and angle > 20:
        return ["Для режима ГОСТ 2037-82 угол наклона должен быть от 0 до 20°."]
    return []


def apply(values: dict, sw=None, selection: dict | None = None,
          design_mode: str | None = None) -> dict:
    if design_mode is None:
        design_mode = json.loads(STATE.read_text(encoding="utf-8")).get("design_mode", "special")
    if selection is None:
        selection = {"tube": "custom", "screw": "custom", "material": "unspecified"}
    errors = validate(values) + validate_selection(values, selection) + validate_design_mode(values, design_mode)
    if errors:
        return {"ok": False, "errors": errors}
    sw = sw or win32.GetActiveObject("SldWorks.Application")
    docs = open_models(sw)
    prepared = {}
    originals = {}
    part_originals = []
    for kind, doc in docs.items():
        mgr, equations = globals_in(doc)
        prepared[kind] = (mgr, equations)
    for key, targets in FIELDS.items():
        for kind, name in targets:
            if name not in prepared[kind][1]:
                raise RuntimeError(f"В {FILES[kind].name} отсутствует переменная «{name}».")
    loaded_parts = {}
    for key, (path, dimension_names) in PART_FIELDS.items():
        if not path.is_file():
            raise RuntimeError(f"Отсутствует деталь опоры: {path.name}")
        part = next((d for d in (sw.GetDocuments or []) if d.GetPathName.lower() == str(path).lower()), None)
        if part is None:
            spec = sw.GetOpenDocSpec(str(path))
            spec.DocumentType = 1
            spec.Silent = True
            spec.ReadOnly = False
            part = sw.OpenDoc7(spec)
        if part is None or bool(part.IsOpenedReadOnly):
            raise RuntimeError(f"Не удалось открыть деталь опоры для изменения: {path.name}")
        dimensions = [part.Parameter(name) for name in dimension_names]
        if any(dim is None for dim in dimensions):
            raise RuntimeError(f"В детали {path.name} отсутствуют размеры вытягивания")
        loaded_parts[key] = (part, dimensions)

    affected_paths = {path.resolve() for path in FILES.values()} | {TOP_ASSEMBLY.resolve()}
    affected_paths.update(path.resolve() for path, _ in PART_FIELDS.values())
    for doc in docs.values():
        for component in doc.GetComponents(False) or []:
            path = Path(component.GetPathName)
            if path.is_file() and (path.resolve().is_relative_to(CAD.resolve()) or
                                   path.resolve().is_relative_to(RECOVERED_CAD.resolve())):
                affected_paths.add(path.resolve())
    loaded = {Path(d.GetPathName).resolve(): d for d in (sw.GetDocuments or []) if d.GetPathName}
    dirty_before = [p.name for p in affected_paths if p in loaded and loaded[p].GetSaveFlag]
    if dirty_before:
        raise RuntimeError("Сохраните несохранённые CAD-файлы перед применением параметров: " + ", ".join(dirty_before))

    snapshot = BASE / "snapshots" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    snapshot.mkdir(parents=True, exist_ok=False)
    for path in sorted(affected_paths):
        if path.is_relative_to(CAD.resolve()):
            target = snapshot / "CAD" / path.relative_to(CAD)
        else:
            target = snapshot / "CAD_восстановленный" / path.relative_to(RECOVERED_CAD)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    try:
        for kind, doc in docs.items():
            activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            sw.ActivateDoc2(doc.GetTitle, False, activate_errors)
            if activate_errors.value != 0:
                raise RuntimeError(f"Не удалось активировать {doc.GetTitle}: {activate_errors.value}")
            for key, targets in FIELDS.items():
                for target_kind, name in targets:
                    if target_kind != kind:
                        continue
                    mgr, equations = prepared[kind]
                    index, old = equations[name]
                    originals[(kind, index)] = old
                    new = equation_for(name, key, values[key])
                    if new != old:
                        set_equation(mgr, index, new)
        for key, (part, dimensions) in loaded_parts.items():
            half_length_m = values[key] / 2000
            for dimension in dimensions:
                old = float(dimension.SystemValue)
                part_originals.append((dimension, old))
                if abs(old - half_length_m) > 1e-9:
                    dimension.SystemValue = half_length_m
                    if abs(float(dimension.SystemValue) - half_length_m) > 1e-9:
                        raise RuntimeError(f"SolidWorks не принял размер {key}")
            if not bool(part.ForceRebuild3(False)):
                raise RuntimeError(f"Не удалось перестроить деталь опоры: {part.GetTitle}")
        rebuilds = {}
        for kind, doc in docs.items():
            activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            sw.ActivateDoc2(doc.GetTitle, False, activate_errors)
            prepared[kind][0].EvaluateAll
            rebuilds[kind] = bool(doc.ForceRebuild3(False))
        if not all(rebuilds.values()):
            raise RuntimeError(f"Перестроение подсборки не удалось: {rebuilds}")
        top = sw.GetOpenDocumentByName(str(TOP_ASSEMBLY))
        activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        sw.ActivateDoc3(top.GetTitle, False, 2, activate_errors)
        if activate_errors.value or not bool(top.ForceRebuild3(False)):
            raise RuntimeError("Не удалось перестроить рабочую сборку после изменения узлов.")
        from open_assembly import model_issues
        suppressed, broken_mates, feature_errors = model_issues(sw, top)
        if suppressed or broken_mates or feature_errors:
            raise RuntimeError(f"После изменения параметров обнаружены ошибки модели: подавлено {suppressed}, потерянные сопряжения {broken_mates}, ошибки элементов {feature_errors[:12]}")
        saves = {}
        loaded = {Path(d.GetPathName).resolve(): d for d in (sw.GetDocuments or []) if d.GetPathName}
        for path in sorted(affected_paths, key=lambda p: (p.suffix.upper() != ".SLDPRT", str(p))):
            doc = loaded.get(path)
            if doc is None or not doc.GetSaveFlag:
                continue
            save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            saved = bool(doc.Save3(1, save_errors, save_warnings))
            saves[str(path.relative_to(BASE))] = {"saved": saved, "errors": save_errors.value, "warnings": save_warnings.value}
        if not all(s["saved"] and s["errors"] == 0 for s in saves.values()):
            raise RuntimeError(f"Ошибка сохранения: {saves}")
        state = {"values": values, "selection": selection, "design_mode": design_mode,
                 "last_applied": datetime.now().isoformat(timespec="seconds"), "rebuilds": rebuilds, "saves": saves}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "snapshot": str(snapshot), **state}
    except Exception:
        for dimension, old in part_originals:
            try:
                dimension.SystemValue = old
            except Exception:
                pass
        for (kind, index), old in originals.items():
            try:
                activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                sw.ActivateDoc2(docs[kind].GetTitle, False, activate_errors)
                set_equation(prepared[kind][0], index, old)
            except Exception:
                pass
        for kind, doc in docs.items():
            try:
                sw.ActivateDoc2(doc.GetTitle, False, win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0))
                prepared[kind][0].EvaluateAll
                doc.ForceRebuild3(False)
            except Exception:
                pass
        try:
            top = sw.GetOpenDocumentByName(str(TOP_ASSEMBLY))
            sw.ActivateDoc3(top.GetTitle, False, 2, win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0))
            top.ForceRebuild3(False)
        except Exception:
            pass
        raise

def main():
    operation = sys.argv[1] if len(sys.argv) > 1 else "state"
    if operation == "state":
        print(STATE.read_text(encoding="utf-8"))
    elif operation == "apply":
        request = json.load(sys.stdin)
        print(json.dumps(apply(request["values"], selection=request.get("selection"),
                               design_mode=request.get("design_mode")), ensure_ascii=False))
    else:
        raise SystemExit("Unknown operation")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        raise SystemExit(1)

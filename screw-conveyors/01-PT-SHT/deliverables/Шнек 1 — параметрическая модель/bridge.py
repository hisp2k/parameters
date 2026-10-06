"""SolidWorks bridge for the supplied shafted screw model."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

import pythoncom
import win32com.client as win32
from standards import validate_selection
from open_assembly import model_issues
from pin_joints import verify as verify_pin_joints
from support_pipe_joints import verify as verify_support_pipe_joints

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
    "incline": [("tube", "Угол наклона"), ("support", "Наклон корпуса от горизонтали")],
    "inlet_diameter": [("tube", "Диаметр патрубка")],
    "inlet_length": [("tube", "Длина патрубка")],
    "inlet_wall": [("tube", "Толщина стенки патрубка")],
    "flange_thickness": [("tube", "Толщина фланца")],
    "mounting_hole_diameter": [("tube", "Отверстие М8")],
    "opening_diameter": [("tube", "Диаметр отверстия корпуса")],
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
    if key == "incline":
        # Tube variable is measured from vertical; support and UI use horizontal.
        native_angle = 90 - value if name == "Угол наклона" else value
        return f'"{name}"= {native_angle:g}градусов'
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


def interference_issues(top) -> list[dict]:
    """Check the actual working configurations, including hidden and multibody solids."""
    mgr = top.InterferenceDetectionManager
    mgr.TreatCoincidenceAsInterference = False
    mgr.TreatSubAssembliesAsComponents = False
    mgr.IncludeMultibodyPartInterferences = True
    mgr.IgnoreHiddenBodies = False
    mgr.MakeInterferingPartsTransparent = False
    mgr.CreateFastenersFolder = False
    try:
        result = []
        for item in mgr.GetInterferences or []:
            volume = float(item.Volume) * 1e9
            if volume > 0.001:
                result.append({"components": [c.Name2 for c in item.Components or []],
                               "volume_mm3": volume})
        return result
    finally:
        mgr.Done()


def refresh_cavities(sw, assembly):
    """Rebuild cavity parts in their owning assembly after their tools changed."""
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    sw.ActivateDoc3(assembly.GetPathName, False, 2, errors)
    if errors.value:
        raise RuntimeError("Не удалось активировать контекст подрезки деталей.")
    visited = set()
    for component in assembly.GetComponents(True) or []:
        part = component.GetModelDoc2
        if part is None or part.GetType != 1 or part.GetPathName in visited:
            continue
        visited.add(part.GetPathName)
        feature = part.FirstFeature
        has_cavity = False
        while feature:
            if feature.GetTypeName2 == "Cavity":
                has_cavity = True
                break
            feature = feature.GetNextFeature
        if not has_cavity:
            continue
        assembly.ClearSelection2(True)
        if not component.Select4(False, assembly.SelectionManager.CreateSelectData, False):
            raise RuntimeError(f"Не удалось выбрать деталь подрезки {component.Name2}")
        info = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        status = assembly.EditPart2(True, False, info)
        try:
            if status != 0 or info.value:
                raise RuntimeError(f"Не удалось открыть контекст {component.Name2}: {status}, {info.value}")
            part.ForceRebuild3(False)
        finally:
            assembly.EditAssembly()
    assembly.ClearSelection2(True)


def measured_geometry(top):
    component = next(c for c in top.GetComponents(False) if "Труба шнека" in c.Name2)
    part = component.GetModelDoc2
    diameter = float(part.Parameter("D1@Эскиз2").SystemValue) * 1000
    surfaces = [list(face.GetSurface.CylinderParams)
                for body in part.GetBodies2(0, True) for face in body.GetFaces()
                if face.GetSurface.IsCylinder]
    outer = next(s for s in surfaces if abs(s[6] * 2000 - diameter) < 1e-5)
    transform = list(component.Transform2.ArrayData)
    axis = [sum(outer[j + 3] * transform[j * 3 + i] for j in range(3)) for i in range(3)]
    box = list(part.GetPartBox(True))
    return {"tube_diameter": outer[6] * 2000, "working_length": (box[4] - box[1]) * 1000 - 270,
            "incline": math.degrees(math.asin(min(1., abs(axis[1])))), "world_axis": axis,
            "horizontal_plane": "XZ; нормаль Y соответствует плоскости опор"}


class ApplyError(RuntimeError):
    """A failed CAD transaction with evidence that rollback was checked."""
    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


def apply(values: dict, sw=None, selection: dict | None = None,
          design_mode: str | None = None) -> dict:
    # Validate before connecting to CAD so invalid requests remain read-only.
    if design_mode is None:
        design_mode = json.loads(STATE.read_text(encoding="utf-8")).get("design_mode", "special")
    if selection is None:
        selection = {"tube": "custom", "screw": "custom", "material": "unspecified"}
    errors = validate(values) + validate_selection(values, selection) + validate_design_mode(values, design_mode)
    if errors:
        return {"ok": False, "errors": errors}
    sw = sw or win32.GetActiveObject("SldWorks.Application")
    previous = sw.CommandInProgress
    sw.CommandInProgress = True
    try:
        return _apply(values, sw, selection, design_mode)
    finally:
        sw.CommandInProgress = previous


def _apply(values: dict, sw=None, selection: dict | None = None,
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
    changed_kinds = set()
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

    original_geometry = measured_geometry(sw.GetOpenDocumentByName(str(TOP_ASSEMBLY)))
    stage = "parameters"
    failure_details = {}
    try:
        for kind, doc in docs.items():
            activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            sw.ActivateDoc3(doc.GetPathName, False, 2, activate_errors)
            if activate_errors.value != 0 or sw.ActiveDoc is None or Path(sw.ActiveDoc.GetPathName).resolve() != Path(doc.GetPathName).resolve():
                raise RuntimeError(f"Не удалось активировать {doc.GetTitle}: {activate_errors.value}")
            for key, targets in FIELDS.items():
                for target_kind, name in targets:
                    if target_kind != kind:
                        continue
                    mgr, equations = prepared[kind]
                    index, old = equations[name]
                    new = equation_for(name, key, values[key])
                    if new != old:
                        originals[(kind, index)] = old
                        changed_kinds.add(kind)
                        set_equation(mgr, index, new)
        for key, (part, dimensions) in loaded_parts.items():
            half_length_m = values[key] / 2000
            changed_part = False
            for dimension in dimensions:
                old = float(dimension.SystemValue)
                if abs(old - half_length_m) > 1e-9:
                    part_originals.append((dimension, old))
                    changed_kinds.add("support")
                    dimension.SystemValue = half_length_m
                    changed_part = True
                    if abs(float(dimension.SystemValue) - half_length_m) > 1e-9:
                        raise RuntimeError(f"SolidWorks не принял размер {key}")
            if changed_part and not bool(part.ForceRebuild3(False)):
                raise RuntimeError(f"Не удалось перестроить деталь опоры: {part.GetTitle}")
        stage = "rebuild"
        rebuilds = {}
        for kind, doc in docs.items():
            activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            sw.ActivateDoc3(doc.GetPathName, False, 2, activate_errors)
            prepared[kind][0].EvaluateAll
            if kind in changed_kinds:
                rebuilds[kind] = bool(doc.ForceRebuild3(False))
                refresh_cavities(sw, doc)
                if not rebuilds[kind]:
                    rebuilds[kind] = bool(doc.ForceRebuild3(False))
        top = sw.GetOpenDocumentByName(str(TOP_ASSEMBLY))
        activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        sw.ActivateDoc3(top.GetPathName, False, 2, activate_errors)
        if activate_errors.value:
            raise RuntimeError("Не удалось активировать рабочую сборку.")
        top_rebuilt = bool(top.ForceRebuild3(False))
        # A changed in-context part may need its updated parent geometry first.
        failed_kinds = [kind for kind in rebuilds if not rebuilds[kind]]
        if failed_kinds:
            for kind in failed_kinds:
                sw.ActivateDoc3(docs[kind].GetPathName, False, 2, activate_errors)
                rebuilds[kind] = bool(docs[kind].ForceRebuild3(False))
            sw.ActivateDoc3(top.GetPathName, False, 2, activate_errors)
            top_rebuilt = bool(top.ForceRebuild3(False))
        if not all(rebuilds.values()):
            failed = {kind: model_issues(sw, doc) for kind, doc in docs.items() if kind in rebuilds and not rebuilds[kind]}
            failure_details["failed_features"] = [
                {"node": kind, "document": row[0], "feature": row[1], "error_code": row[2]}
                for kind, issues in failed.items() for row in issues[2]]
            raise RuntimeError(f"Перестроение подсборки не удалось: {rebuilds}; ошибки узлов: {failed}")
        if not top_rebuilt:
            raise RuntimeError("Не удалось перестроить рабочую сборку после изменения узлов.")
        stage = "verification"
        suppressed, broken_mates, feature_errors = model_issues(sw, top)
        if suppressed or broken_mates or feature_errors:
            failure_details["failed_features"] = [
                {"node": "top", "document": row[0], "feature": row[1], "error_code": row[2]}
                for row in feature_errors]
            raise RuntimeError(f"После изменения параметров обнаружены ошибки модели: подавлено {suppressed}, потерянные сопряжения {broken_mates}, ошибки элементов {feature_errors[:12]}")
        geometry = measured_geometry(top)
        for key in ("working_length", "tube_diameter", "incline"):
            if abs(geometry[key] - values[key]) > 1e-4:
                raise RuntimeError(f"Геометрия не соответствует запросу: {key}, задано {values[key]}, в CAD {geometry[key]}")
        pin_joints = verify_pin_joints(top)
        pipe_joints = verify_support_pipe_joints(docs['support'])
        intersections = interference_issues(top)
        if intersections:
            failure_details["interferences"] = intersections
            raise RuntimeError(f"После перестроения обнаружены объёмные пересечения (более 0,001 мм³): {intersections[:8]}")
        stage = "save"
        saves = {}
        loaded = {Path(d.GetPathName).resolve(): d for d in (sw.GetDocuments or []) if d.GetPathName}
        for path in sorted(affected_paths, key=lambda p: (p.suffix.upper() != ".SLDPRT", str(p))):
            doc = loaded.get(path)
            if doc is None or not doc.GetSaveFlag:
                continue
            save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            save_options = 1 | 8 | (4 if doc.GetType == 2 else 0)  # Already rebuilt and checked; save referenced CAD without a second rebuild.
            saved = bool(doc.Save3(save_options, save_errors, save_warnings))
            saves[str(path.relative_to(BASE))] = {"saved": saved, "errors": save_errors.value, "warnings": save_warnings.value}
        if not all(s["saved"] and s["errors"] == 0 for s in saves.values()):
            raise RuntimeError(f"Ошибка сохранения: {saves}")
        state = {"values": values, "selection": selection, "design_mode": design_mode,
                 "last_applied": datetime.now().isoformat(timespec="seconds"), "rebuilds": rebuilds, "saves": saves,
                 "rebuilt_nodes": sorted(changed_kinds) + ["top"],
                 "cad_verification": {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                     "components": len(top.GetComponents(False) or []), "suppressed": suppressed,
                     "broken_mates": broken_mates, "feature_errors": len(feature_errors),
                     "positive_interferences": 0, "threshold_mm3": 0.001,
                     "measured_geometry": geometry,
                     "pin_joints": pin_joints,
                     "support_pipe_joints": pipe_joints,
                     "representation": "Сборочная — резьба условно"}}
        temporary_state = STATE.with_name(f"state.{os.getpid()}.tmp")
        temporary_state.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary_state, STATE)
        return {"ok": True, "snapshot": str(snapshot), **state}
    except Exception as failure:
        for dimension, old in part_originals:
            try:
                dimension.SystemValue = old
            except Exception:
                pass
        for (kind, index), old in originals.items():
            try:
                activate_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                sw.ActivateDoc3(docs[kind].GetPathName, False, 2, activate_errors)
                set_equation(prepared[kind][0], index, old)
            except Exception:
                pass
        for kind, doc in docs.items():
            if kind not in changed_kinds:
                continue
            try:
                sw.ActivateDoc3(doc.GetPathName, False, 2, win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0))
                prepared[kind][0].EvaluateAll
                doc.ForceRebuild3(False)
                refresh_cavities(sw, doc)
                doc.ForceRebuild3(False)
            except Exception:
                pass
        try:
            top = sw.GetOpenDocumentByName(str(TOP_ASSEMBLY))
            sw.ActivateDoc3(top.GetPathName, False, 2, win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0))
            top.ForceRebuild3(False)
        except Exception:
            pass
        # Rollback is part of the transaction: validate and persist restored geometry.
        restored = model_issues(sw, top)
        if restored != (0, 0, []):
            raise RuntimeError(f"Не удалось полностью восстановить модель: {restored}. Резервная копия: {snapshot}")
        restored_pin_joints = verify_pin_joints(top)
        restored_pipe_joints = verify_support_pipe_joints(docs['support'])
        restored_intersections = interference_issues(top)
        if restored_intersections:
            raise RuntimeError(f"После возврата остались пересечения: {restored_intersections[:8]}. Резервная копия: {snapshot}")
        save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        if not top.Save3(13, save_errors, save_warnings) or save_errors.value:
            raise RuntimeError(f"Восстановленная модель не сохранена: {save_errors.value}. Резервная копия: {snapshot}")
        restored_geometry = measured_geometry(top)
        for key in ("working_length", "tube_diameter", "incline"):
            if abs(restored_geometry[key] - original_geometry[key]) > 1e-4:
                raise RuntimeError(f"Откат не восстановил размер {key}: до изменения {original_geometry[key]}, после {restored_geometry[key]}. Резервная копия: {snapshot}")
        raise ApplyError(str(failure), {
            "code": "cad_apply_failed", "failure_stage": stage,
            "snapshot": str(snapshot), "rollback_verified": True,
            "restored_geometry": restored_geometry, **failure_details,
            "restored_pin_joints": restored_pin_joints,
            "restored_support_pipe_joints": restored_pipe_joints,
        }) from failure

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
        print(json.dumps({"ok": False, "errors": [str(exc)],
                          **getattr(exc, "details", {})}, ensure_ascii=False))
        raise SystemExit(1)

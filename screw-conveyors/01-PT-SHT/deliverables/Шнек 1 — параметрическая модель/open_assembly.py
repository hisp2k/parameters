"""Open the delivered assembly in SolidWorks and report the actual load state."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pythoncom
import win32com.client as win32


BASE = Path(__file__).resolve().parent
ASSEMBLY = BASE / "CAD_восстановленный" / "PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"


def model_issues(sw, top):
    previous = sw.CommandInProgress
    sw.CommandInProgress = True
    try:
        return _model_issues(sw, top)
    finally:
        sw.CommandInProgress = previous


def _model_issues(sw, top):
    suppressed = sum(int(c.GetSuppression) == 0 for c in (top.GetComponents(False) or []))
    broken_mates = 0
    other_errors = []
    documents_by_path = {top.GetPathName: top}
    for component in top.GetComponents(False) or []:
        model = component.GetModelDoc2
        if model and model.GetPathName:
            documents_by_path[model.GetPathName] = model
    documents = list(documents_by_path.values())
    for doc in documents:
        feature = doc.FirstFeature
        while feature:
            if feature.GetErrorCode and feature.GetTypeName2 != 'MateGroup':
                other_errors.append((doc.GetTitle, feature.Name, int(feature.GetErrorCode)))
            if feature.GetTypeName2 == 'MateGroup':
                mate = feature.GetFirstSubFeature
                while mate:
                    if int(mate.GetErrorCode) == 48:
                        broken_mates += 1
                    elif mate.GetErrorCode:
                        other_errors.append((doc.GetTitle, mate.Name, int(mate.GetErrorCode)))
                    mate = mate.GetNextSubFeature
            feature = feature.GetNextFeature
    return suppressed, broken_mates, other_errors


def open_assembly() -> dict:
    if not ASSEMBLY.is_file():
        return {"ok": False, "error": "Файл главной сборки не найден."}

    try:
        sw = win32.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32.Dispatch("SldWorks.Application")
    sw.Visible = True

    doc = sw.GetOpenDocumentByName(str(ASSEMBLY))
    load_error = 0
    if doc is None:
        spec = sw.GetOpenDocSpec(str(ASSEMBLY))
        spec.DocumentType = 2  # swDocASSEMBLY
        spec.ReadOnly = False
        spec.Silent = True
        doc = sw.OpenDoc7(spec)
        load_error = int(spec.Error)
    if doc is None:
        return {"ok": False, "error": f"SolidWorks не открыл сборку (код {load_error})."}
    if Path(doc.GetPathName).resolve() != ASSEMBLY.resolve():
        return {"ok": False, "error": "SolidWorks открыл документ с тем же именем из другой папки."}

    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    activated = sw.ActivateDoc3(doc.GetPathName, False, 2, errors)
    if activated is None or errors.value:
        return {"ok": False, "error": f"Сборка загружена, но не отображена (код {errors.value})."}

    components = doc.GetComponents(False) or []
    missing = Counter()
    for component in components:
        component_path = component.GetPathName
        if component_path and not Path(component_path).is_file():
            missing[Path(component_path).name] += 1
    local_by_name = {}
    for path in ASSEMBLY.parent.rglob("*"):
        if path.is_file():
            local_by_name.setdefault(path.name.casefold(), []).append(path)
    relink_candidates = {
        name: [str(path.relative_to(ASSEMBLY.parent)) for path in local_by_name[name.casefold()]]
        for name in missing if name.casefold() in local_by_name
    }
    suppressed, broken_mates, other_errors = model_issues(sw, doc)
    return {
        "ok": True,
        "components": len(components),
        "partial": bool(missing) or bool(load_error & 2) or bool(suppressed) or bool(broken_mates) or bool(other_errors),
        "missing_references": sum(missing.values()),
        "missing_files": len(missing),
        "suppressed_components": suppressed,
        "broken_mates": broken_mates,
        "other_feature_errors": len(other_errors),
        "relink_candidates": relink_candidates,
        "load_error": load_error,
        "message": (
            f"Сборка открыта: {len(components)} вхождений; неразрешённых путей — "
            f"{sum(missing.values())}; подавленных компонентов — {suppressed}; "
            f"ошибочных сопряжений — {broken_mates}; других ошибок элементов — {len(other_errors)}."
        ),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(open_assembly(), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Ошибка SolidWorks: {exc}"}, ensure_ascii=False))

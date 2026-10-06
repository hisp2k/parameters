"""Create linked SolidWorks drawings from the saved assembly models."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pythoncom
import win32com.client as win32
from open_assembly import model_issues

BASE = Path(__file__).resolve().parent
CAD = BASE / "CAD"
RECOVERED_CAD = BASE / "CAD_восстановленный"
DRAWINGS = BASE / "Чертежи"
TEMPLATE = Path(r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-assly drw.drwdot")
SOURCES = (
    ("Сборка шнека", RECOVERED_CAD / "PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"),
    ("Труба в сборе", RECOVERED_CAD / "Труба в сборе — исправлено 20261004" / "PT.SHT.01.21.00.00 СБ 'Труба в сборе' — исправлено.SLDASM"),
    ("Шнековый вал", RECOVERED_CAD / "Шнековый вал — исправлено 20261004" / "PT.SHT.01.24.00.00 СБ 'Шнековый вал' — исправлено.SLDASM"),
)


def _views(drawing):
    view = drawing.GetFirstView
    result = []
    while view:
        if view.GetReferencedModelName:
            result.append(view)
        view = view.GetNextView
    return result


def _set_fitting_scale(drawing):
    sheet = drawing.GetCurrentSheet
    width, height = sheet.GetProperties[-2:]
    for denominator in (30, 40, 50, 60, 80, 100):
        sheet.SetScale(1, denominator, True, True)
        drawing.ForceRebuild3(False)
        outlines = [view.GetOutline for view in _views(drawing)]
        if all(x0 >= .01 and y0 >= .01 and x1 <= width - .01 and y1 <= height - .01
               for x0, y0, x1, y1 in outlines):
            return denominator
    raise RuntimeError("Виды чертежа не помещаются в формат шаблона.")


def generate() -> dict:
    if not TEMPLATE.is_file():
        raise RuntimeError("Шаблон чертежа ГОСТ SolidWorks не найден.")
    if any(not source.is_file() for _, source in SOURCES):
        raise RuntimeError("Отсутствует файл одной из основных сборок.")
    try:
        sw = win32.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32.Dispatch("SldWorks.Application")
    sw.Visible = True
    batch = DRAWINGS / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    batch.mkdir(parents=True, exist_ok=False)
    results = []
    for label, source in SOURCES:
        spec = sw.GetOpenDocSpec(str(source))
        spec.DocumentType = 2
        spec.ReadOnly = True
        spec.Silent = True
        model = sw.OpenDoc7(spec)
        if model is None:
            raise RuntimeError(f"Не удалось открыть модель «{label}» (код {spec.Error}).")
        missing = sum(bool(component.GetPathName) and not Path(component.GetPathName).is_file()
                      for component in (model.GetComponents(False) or []))
        suppressed, broken_mates, other_errors = (model_issues(sw, model) if label == "Сборка шнека"
                                                   else (0, 0, []))
        drawing = sw.NewDocument(str(TEMPLATE), 0, 0, 0)
        if drawing is None or drawing.GetType != 3:
            raise RuntimeError(f"Не удалось создать чертёж «{label}».")
        if not drawing.Create1stAngleViews2(str(source)):
            raise RuntimeError(f"SolidWorks не построил виды для «{label}».")
        scale = _set_fitting_scale(drawing)
        views = _views(drawing)
        if len(views) != 3 or any(Path(v.GetReferencedModelName).resolve() != source.resolve() for v in views):
            raise RuntimeError(f"Виды чертежа «{label}» не связаны с исходной моделью.")
        output = batch / f"{label} {batch.name}.SLDDRW"
        save_error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        save_warning = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        saved = bool(drawing.SaveAs4(str(output), 0, 2, save_error, save_warning))
        if not saved or save_error.value or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"Не удалось сохранить чертёж «{label}» (код {save_error.value}).")
        results.append({
            "name": label,
            "path": str(output.relative_to(BASE)),
            "views": len(views),
            "scale": f"1:{scale}",
            "load_error": int(spec.Error),
            "missing_references": missing,
            "suppressed_components": suppressed,
            "broken_mates": broken_mates,
            "other_feature_errors": len(other_errors),
        })
        sw.CloseDoc(drawing.GetTitle)
    return {"ok": True, "batch": str(batch.relative_to(BASE)), "drawings": results,
            "partial": any(item["missing_references"] or item["suppressed_components"] or
                           item["broken_mates"] or item["other_feature_errors"] or
                           item["load_error"] & 2 for item in results)}


if __name__ == "__main__":
    try:
        print(json.dumps(generate(), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))

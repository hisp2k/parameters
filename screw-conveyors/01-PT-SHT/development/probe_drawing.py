from pathlib import Path
import pythoncom
import win32com.client as win32

base = (Path('outputs') / 'Шнек 1 — параметрическая модель').resolve()
model_path = base / 'CAD' / "PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"
template = Path(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-assly drw.drwdot')
out = Path('work/probe_assembly.SLDDRW').resolve()
try:
    sw = win32.GetActiveObject('SldWorks.Application')
except Exception:
    sw = win32.Dispatch('SldWorks.Application')
sw.Visible = True
spec = sw.GetOpenDocSpec(str(model_path))
spec.DocumentType = 2
spec.ReadOnly = True
spec.Silent = True
model = sw.OpenDoc7(spec)
print('model', bool(model), spec.Error)
drawing = sw.NewDocument(str(template), 0, 0, 0)
print('drawing', bool(drawing))
if drawing:
    sheet = drawing.GetCurrentSheet
    print('props', sheet.GetProperties)
    print('type', drawing.GetType, 'active_type', sw.ActiveDoc.GetType if sw.ActiveDoc else None)
    print('model_path', model.GetPathName)
    width, height = sheet.GetProperties[-2:]
    print('1views', drawing.Create1stAngleViews2(str(model_path)))
    print('set_scale', sheet.SetScale(1, 30, True, True))
    front = drawing.CreateDrawViewFromModelView3(str(model_path), '*Front', width*0.35, height*0.55, 0)
    iso = drawing.CreateDrawViewFromModelView3(str(model_path), '*Isometric', width*0.75, height*0.55, 0)
    print('views', bool(front), bool(iso))
    print('rebuild', drawing.ForceRebuild3(False))
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    try:
        result = drawing.Extension.SaveAs(str(out), 0, 1, None, errors, warnings)
        print('save', result, errors.value, warnings.value, out.exists(), out.stat().st_size if out.exists() else 0)
    except Exception as exc:
        print('save_error', str(exc)[:200])
    print('save3', drawing.SaveAs3(str(out), 0, 2), out.exists(), out.stat().st_size if out.exists() else 0)
    save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    print('save4', drawing.SaveAs4(str(out), 0, 2, save_errors, save_warnings), save_errors.value, save_warnings.value)
    view = drawing.GetFirstView
    names = []
    while view:
        names.append((view.Name, view.GetReferencedModelName if hasattr(view,'GetReferencedModelName') else None, view.GetOutline if hasattr(view,'GetOutline') else None))
        view = view.GetNextView
    print('view_names', names)

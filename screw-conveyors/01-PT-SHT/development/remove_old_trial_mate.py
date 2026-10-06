from pathlib import Path
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
path = (Path('work') / 'mate_trial' / 'CAD_восстановленный' / 'Шнек 1 — испытание сопряжений.SLDASM').resolve()
doc = sw.GetOpenDocumentByName(str(path))
if doc is None:
    raise RuntimeError('Trial assembly is not open')
error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, error)
if error.value:
    raise RuntimeError(f'Activation error {error.value}')
group = doc.FirstFeature
old = replacement = None
while group:
    if group.GetTypeName2 == 'MateGroup':
        feature = group.GetFirstSubFeature
        while feature:
            if feature.Name == 'Концентричный75': old = feature
            if feature.Name == 'Концентричный98': replacement = feature
            feature = feature.GetNextSubFeature
    group = group.GetNextFeature
if not old or not replacement or replacement.GetErrorCode:
    raise RuntimeError('Missing old or healthy replacement mate')
doc.ClearSelection2(True)
print('selected', old.Select2(False, 0), flush=True)
print('deleted', doc.Extension.DeleteSelection2(0), flush=True)
doc.EditRebuild3
broken = 0
group = doc.FirstFeature
while group:
    if group.GetTypeName2 == 'MateGroup':
        feature = group.GetFirstSubFeature
        while feature:
            broken += feature.GetErrorCode == 48
            feature = feature.GetNextSubFeature
    group = group.GetNextFeature
print('remaining broken in top', broken, flush=True)
if broken != 33:
    raise RuntimeError('Expected 33 broken mates after replacement; trial left unsaved')
save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
print('saved', doc.Save3(1, save_errors, save_warnings), save_errors.value, save_warnings.value, flush=True)

"""Repair one bolt concentric mate on the disposable assembly copy."""
from math import dist
from pathlib import Path
import pythoncom
import win32com.client as win32

path = (Path('work') / 'mate_trial' / 'CAD_восстановленный' / 'Шнек 1 — испытание сопряжений.SLDASM').resolve()
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(path))
if doc is None:
    raise RuntimeError('Trial assembly must be open')
error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, error)
if error.value:
    raise RuntimeError(f'Activation failed: {error.value}')

def broken_count():
    count = 0
    top = doc.FirstFeature
    while top:
        if top.GetTypeName2 == 'MateGroup':
            item = top.GetFirstSubFeature
            while item:
                count += item.GetErrorCode == 48
                item = item.GetNextSubFeature
        top = top.GetNextFeature
    return count

def find_mate(name):
    top = doc.FirstFeature
    while top:
        if top.GetTypeName2 == 'MateGroup':
            item = top.GetFirstSubFeature
            while item:
                if item.Name == name:
                    return item
                item = item.GetNextSubFeature
        top = top.GetNextFeature
    raise KeyError(name)

before = broken_count()
old = find_mate('Концентричный73')
if old.GetErrorCode != 48:
    raise RuntimeError('Target mate is not broken')
mate = old.GetSpecificFeature2
missing = mate.MateEntity(0)
component = missing.ReferenceComponent
position_before = tuple(component.Transform2.ArrayData[9:12])
radius = float(missing.EntityParams[6])
faces = [face for body in component.GetModelDoc2.GetBodies2(0, True) or []
         for face in body.GetFaces() or []
         if face.GetSurface.IsCylinder
         and abs(float(face.GetSurface.CylinderParams[6]) - radius) < 1e-6]
print('candidate cylindrical faces', len(faces), flush=True)
if len(faces) != 2:
    raise RuntimeError('Ambiguous bolt shaft geometry')
candidate = component.GetCorrespondingEntity(faces[0])
if candidate is None:
    raise RuntimeError('Corresponding assembly face missing')
other = old.GetDefinition.EntitiesToMate[1]
if other is None:
    raise RuntimeError('Other mate reference missing')
doc.ClearSelection2(True)
select_data = doc.SelectionManager.CreateSelectData
select_data.Mark = 1
if not candidate.Select4(False, select_data) or not other.Select4(True, select_data):
    raise RuntimeError('Cannot select the mate faces')
if doc.SelectionManager.GetSelectedObjectCount2(1) != 2:
    raise RuntimeError('Unexpected mate selection')
replacement = doc.CreateMateData(1)
replacement.MateAlignment = old.GetDefinition.MateAlignment
created = doc.CreateMate(replacement)
if created is None or created.GetErrorCode:
    raise RuntimeError('Replacement mate could not be created')
position_after = tuple(component.Transform2.ArrayData[9:12])
shift_mm = dist(position_before, position_after) * 1000
print('component shift mm', shift_mm, flush=True)
if shift_mm > 1.0:
    raise RuntimeError('Component shifted too far; do not save trial')
doc.ClearSelection2(True)
if not old.Select2(False, 0) or not doc.Extension.DeleteSelection2(0):
    raise RuntimeError('Cannot remove broken mate')
doc.EditRebuild3
after = broken_count()
print('broken before/after', before, after, flush=True)
if after != before - 1:
    raise RuntimeError('Mate error count did not fall by one')
save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
saved = doc.Save3(1, save_errors, save_warnings)
print('saved', saved, save_errors.value, save_warnings.value, flush=True)
if not saved or save_errors.value:
    raise RuntimeError('Trial save failed')

"""Apply two tested bolt mate repairs to the working assembly."""
from hashlib import sha256
from math import dist
from pathlib import Path
import pythoncom
import win32com.client as win32

base = next(Path('outputs').glob('Шнек 1 — параметрическая модель')).resolve()
path = base / 'CAD_восстановленный' / "PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"
snapshot = base / 'snapshots' / '20261004-mate-repair-before' / path.name
if sha256(path.read_bytes()).digest() != sha256(snapshot.read_bytes()).digest():
    raise RuntimeError('Working file differs from the verified snapshot')

sw = win32.GetActiveObject('SldWorks.Application')
doc = next((candidate for candidate in (sw.GetDocuments or [])
            if candidate.GetPathName and Path(candidate.GetPathName).resolve() == path.resolve()), None)
if doc is None:
    spec = sw.GetOpenDocSpec(str(path))
    spec.DocumentType = 2
    spec.ReadOnly = False
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
    if doc is None or spec.Error:
        raise RuntimeError(f'Could not open working assembly: {spec.Error}')
if doc is None or Path(doc.GetPathName).resolve() != path.resolve():
    raise RuntimeError('Expected working assembly is not open')
print('working assembly save flag after opening', bool(doc.GetSaveFlag), flush=True)
activation_error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, activation_error)
if activation_error.value:
    raise RuntimeError(f'Cannot activate working assembly: {activation_error.value}')

def mates():
    top = doc.FirstFeature
    while top:
        if top.GetTypeName2 == 'MateGroup':
            feature = top.GetFirstSubFeature
            while feature:
                yield feature
                feature = feature.GetNextSubFeature
        top = top.GetNextFeature

def broken_count():
    return sum(feature.GetErrorCode == 48 for feature in mates())

def repair(name):
    old = next((item for item in mates() if item.Name == name), None)
    if old is None or old.GetErrorCode != 48:
        raise RuntimeError(f'Unexpected old mate state: {name}')
    entity = old.GetSpecificFeature2.MateEntity(0)
    component = entity.ReferenceComponent
    if not component.Name2.startswith('Болт М8х25 DIN 933-'):
        raise RuntimeError('Unexpected component for ' + name)
    position_before = tuple(component.Transform2.ArrayData[9:12])
    radius = float(entity.EntityParams[6])
    faces = [face for body in component.GetModelDoc2.GetBodies2(0, True) or []
             for face in body.GetFaces() or []
             if face.GetSurface.IsCylinder
             and abs(float(face.GetSurface.CylinderParams[6]) - radius) < 1e-6]
    if len(faces) != 2:
        raise RuntimeError(f'Ambiguous cylindrical surfaces in {component.Name2}')
    replacement_face = component.GetCorrespondingEntity(faces[0])
    other = old.GetDefinition.EntitiesToMate[1]
    if replacement_face is None or other is None:
        raise RuntimeError('Mate reference could not be resolved')
    doc.ClearSelection2(True)
    selection = doc.SelectionManager.CreateSelectData
    selection.Mark = 1
    if not replacement_face.Select4(False, selection) or not other.Select4(True, selection):
        raise RuntimeError('Mate faces could not be selected')
    if doc.SelectionManager.GetSelectedObjectCount2(1) != 2:
        raise RuntimeError('Unexpected mate selection')
    data = doc.CreateMateData(1)
    data.MateAlignment = old.GetDefinition.MateAlignment
    created = doc.CreateMate(data)
    if created is None or created.GetErrorCode:
        raise RuntimeError('Replacement mate is invalid')
    shift_mm = dist(position_before, tuple(component.Transform2.ArrayData[9:12])) * 1000
    if shift_mm > 1.0:
        raise RuntimeError(f'Unexpected bolt shift: {shift_mm:.3f} mm')
    doc.ClearSelection2(True)
    if not old.Select2(False, 0) or not doc.Extension.DeleteSelection2(0):
        raise RuntimeError('Could not remove old broken mate')
    doc.EditRebuild3
    print(name, component.Name2, f'shift {shift_mm:.3f} mm', flush=True)

print('broken before', broken_count(), flush=True)
if broken_count() != 34:
    raise RuntimeError('Unexpected baseline error count')
repair('Концентричный75')
repair('Концентричный73')
print('broken after', broken_count(), flush=True)
if broken_count() != 32:
    raise RuntimeError('Expected two fewer broken mates')
save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
saved = doc.Save3(1, save_errors, save_warnings)
print('saved', saved, save_errors.value, save_warnings.value, flush=True)
if not saved or save_errors.value:
    raise RuntimeError('Saving repaired assembly failed')

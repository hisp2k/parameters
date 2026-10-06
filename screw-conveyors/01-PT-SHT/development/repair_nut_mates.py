"""Restore two M8 bolt/nut concentric mates in a chosen open assembly."""
from math import dist
from pathlib import Path
import sys
import pythoncom
import win32com.client as win32

target = Path(sys.argv[1]).resolve()
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(target))
if doc is None or Path(doc.GetPathName).resolve() != target:
    raise RuntimeError('Expected assembly is not open')

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
    return sum(f.GetErrorCode == 48 for f in mates())

def face_for(entity):
    comp = entity.ReferenceComponent
    radius = float(entity.EntityParams[6])
    faces = [face for body in comp.GetModelDoc2.GetBodies2(0, True) or []
             for face in body.GetFaces() or []
             if face.GetSurface.IsCylinder
             and abs(float(face.GetSurface.CylinderParams[6]) - radius) < 1e-6]
    if len(faces) != 2:
        raise RuntimeError(f'Ambiguous cylindrical face: {comp.Name2}, {len(faces)}')
    return comp.GetCorrespondingEntity(faces[0])

before = broken_count()
print('before', before, flush=True)
for name, bolt_suffix, nut_suffix in [('Концентричный86', '-1', '-1'), ('Концентричный87', '-9', '-9')]:
    old = next((f for f in mates() if f.Name == name), None)
    if old is None or old.GetErrorCode != 48:
        raise RuntimeError(f'Unexpected mate {name}')
    entities = [old.GetSpecificFeature2.MateEntity(i) for i in (0, 1)]
    bolt, nut = [e.ReferenceComponent for e in entities]
    if not bolt.Name2.startswith('Болт М8х25 DIN 933'+bolt_suffix) or not nut.Name2.startswith('Гайка М8 DIN 934'+nut_suffix):
        raise RuntimeError('Unexpected hardware')
    positions = [tuple(c.Transform2.ArrayData[9:12]) for c in (bolt, nut)]
    faces = [face_for(e) for e in entities]
    if any(f is None for f in faces):
        raise RuntimeError('Assembly face missing')
    doc.ClearSelection2(True)
    selection = doc.SelectionManager.CreateSelectData
    selection.Mark = 1
    if not faces[0].Select4(False, selection) or not faces[1].Select4(True, selection):
        raise RuntimeError('Mate selection failed')
    data = doc.CreateMateData(1)
    data.MateAlignment = old.GetDefinition.MateAlignment
    created = doc.CreateMate(data)
    if created is None or created.GetErrorCode:
        raise RuntimeError(f'New mate invalid: {name}')
    shifts = [dist(before_pos, tuple(c.Transform2.ArrayData[9:12]))*1000
              for before_pos, c in zip(positions, (bolt, nut))]
    print(name, 'shifts_mm', shifts, flush=True)
    if max(shifts) > 1:
        raise RuntimeError(f'Excessive component movement: {name}')
    doc.ClearSelection2(True)
    if not old.Select2(False, 0) or not doc.Extension.DeleteSelection2(0):
        raise RuntimeError(f'Cannot remove old mate: {name}')

after = broken_count()
print('after', after, flush=True)
if after != before - 2:
    raise RuntimeError('Error count did not decrease by two')
errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
saved = doc.Save3(1, errors, warnings)
print('saved', saved, errors.value, warnings.value, flush=True)
if not saved or errors.value:
    raise RuntimeError('Save failed')

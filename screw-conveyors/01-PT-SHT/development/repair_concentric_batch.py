"""Replace specified broken concentric mates after geometric and movement checks."""
from math import dist
from pathlib import Path
import sys
import pythoncom
import win32com.client as win32

path = Path(sys.argv[1]).resolve()
names = sys.argv[2:]
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(path))
if doc is None or Path(doc.GetPathName).resolve() != path:
    raise RuntimeError('Target assembly is not open')

def mates():
    top = doc.FirstFeature
    while top:
        if top.GetTypeName2 == 'MateGroup':
            f = top.GetFirstSubFeature
            while f:
                yield f
                f = f.GetNextSubFeature
        top = top.GetNextFeature

def count():
    return sum(f.GetErrorCode == 48 for f in mates())

def replacement(entity, existing):
    if entity.Reference is not None:
        if existing is None:
            raise RuntimeError('Existing reference could not be selected')
        return existing
    component = entity.ReferenceComponent
    radius = float(entity.EntityParams[6])
    faces = [face for body in component.GetModelDoc2.GetBodies2(0, True) or []
             for face in body.GetFaces() or []
             if face.GetSurface.IsCylinder
             and abs(float(face.GetSurface.CylinderParams[6]) - radius) < 1e-6]
    if len(faces) not in (1, 2):
        raise RuntimeError(f'Ambiguous cylinder on {component.Name2}: {len(faces)}')
    if len(faces) == 2:
        a, b = [face.GetSurface.CylinderParams for face in faces]
        if abs(sum(a[i]*b[i] for i in (3, 4, 5))) < 0.99999:
            raise RuntimeError(f'Different cylinder axes on {component.Name2}')
    result = component.GetCorrespondingEntity(faces[0])
    if result is None:
        raise RuntimeError(f'Assembly face missing for {component.Name2}')
    return result

start = count()
print('before', start, flush=True)
for name in names:
    old = next((f for f in mates() if f.Name == name), None)
    if old is None or old.GetTypeName2 != 'MateConcentric' or old.GetErrorCode != 48:
        raise RuntimeError(f'Unexpected mate: {name}')
    mate = old.GetSpecificFeature2
    entities = [mate.MateEntity(i) for i in (0, 1)]
    components = [e.ReferenceComponent for e in entities]
    positions = [tuple(c.Transform2.ArrayData[9:12]) for c in components]
    old_faces = old.GetDefinition.EntitiesToMate
    faces = [replacement(e, old_faces[i]) for i, e in enumerate(entities)]
    doc.ClearSelection2(True)
    selection = doc.SelectionManager.CreateSelectData
    selection.Mark = 1
    if not faces[0].Select4(False, selection) or not faces[1].Select4(True, selection):
        raise RuntimeError(f'Cannot select faces: {name}')
    data = doc.CreateMateData(1)
    data.MateAlignment = old.GetDefinition.MateAlignment
    created = doc.CreateMate(data)
    if created is None or created.GetErrorCode:
        raise RuntimeError(f'New mate invalid: {name}')
    shifts = [dist(p, tuple(c.Transform2.ArrayData[9:12]))*1000 for p, c in zip(positions, components)]
    print(name, 'shift mm', [round(s, 4) for s in shifts], flush=True)
    if max(shifts) > 1:
        raise RuntimeError(f'Unexpected component movement: {name}')
    doc.ClearSelection2(True)
    if not old.Select2(False, 0) or not doc.Extension.DeleteSelection2(0):
        raise RuntimeError(f'Cannot delete old mate: {name}')
    expected = start - names.index(name) - 1
    actual = count()
    print('remaining', actual, flush=True)
    if actual != expected:
        raise RuntimeError(f'Error count mismatch: {name}: {actual} != {expected}')

errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
saved = doc.Save3(1, errors, warnings)
print('saved', saved, errors.value, warnings.value, flush=True)
if not saved or errors.value:
    raise RuntimeError('Save failed')

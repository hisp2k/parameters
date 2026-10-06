from pathlib import Path
import pythoncom
import win32com.client as win32

path = (Path('work') / 'mate_trial' / 'CAD_восстановленный' / 'Шнек 1 — испытание сопряжений.SLDASM').resolve()
sw = win32.GetActiveObject('SldWorks.Application')
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.Silent = True
spec.ReadOnly = False
doc = sw.OpenDoc7(spec)
if not doc:
    raise RuntimeError(f'Cannot open trial model: {spec.Error}')
activation_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, activation_errors)
print('activation', activation_errors.value, flush=True)

def mate_feature(name):
    group = doc.FirstFeature
    while group:
        if group.GetTypeName2 == 'MateGroup':
            feature = group.GetFirstSubFeature
            while feature:
                if feature.Name == name:
                    return feature
                feature = feature.GetNextSubFeature
        group = group.GetNextFeature
    raise KeyError(name)

feature = mate_feature('Концентричный75')
print('before', feature.GetErrorCode, flush=True)
mate = feature.GetSpecificFeature2
missing = mate.MateEntity(0)
component = missing.ReferenceComponent
part = component.GetModelDoc2
candidates = []
for body in part.GetBodies2(0, True) or []:
    for face in body.GetFaces() or []:
        surface = face.GetSurface
        if surface.IsCylinder:
            radius = float(surface.CylinderParams[6])
            if abs(radius - missing.EntityParams[6]) < 1e-6:
                candidates.append(face)
print('candidate faces', len(candidates), flush=True)
if len(candidates) != 2:
    raise RuntimeError('Unexpected cylinder candidates; not changing mate')
candidate = component.GetCorrespondingEntity(candidates[0])
print('corresponding face', candidate is not None, flush=True)
if candidate is None:
    raise RuntimeError('No assembly-context face')
definition = feature.GetDefinition
entities = definition.EntitiesToMate
print('old entities', [item is not None for item in entities], flush=True)
replacement = doc.CreateMateData(1)
doc.ClearSelection2(True)
selection = doc.SelectionManager.CreateSelectData
selection.Mark = 1
print('selected candidate', candidate.Select4(False, selection), flush=True)
print('selected other', entities[1].Select4(True, selection), flush=True)
print('selection count', doc.SelectionManager.GetSelectedObjectCount2(1), flush=True)
replacement.MateAlignment = definition.MateAlignment
print('new entities', replacement.EntitiesToMate, flush=True)
created = doc.CreateMate(replacement)
changed = created is not None
doc.EditRebuild3
print('created', changed, 'new error', created.GetErrorCode if created else None,
      'old error', feature.GetErrorCode, flush=True)
if changed and not created.GetErrorCode:
    save_errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    save_warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    saved = doc.Save3(1, save_errors, save_warnings)
    print('saved trial', saved, save_errors.value, save_warnings.value, flush=True)
else:
    print('trial not saved', flush=True)

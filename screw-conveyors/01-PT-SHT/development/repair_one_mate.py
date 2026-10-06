from pathlib import Path
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
base = next(Path('outputs').glob('Шнек 1 — параметрическая модель')).resolve()
top = next(d for d in (sw.GetDocuments or []) if d.GetType == 2 and
           str(base).casefold() in d.GetPathName.casefold() and
           '20.00.00' in d.GetTitle and '— восстановлено' in d.GetTitle)

target = None
feature = top.FirstFeature
while feature:
    if feature.GetTypeName2 == 'MateGroup':
        child = feature.GetFirstSubFeature
        while child:
            if child.Name == 'Концентричный75':
                target = child
                break
            child = child.GetNextSubFeature
    if target:
        break
    feature = feature.GetNextFeature
if target is None:
    raise RuntimeError('Mate not found')
mate = target.GetSpecificFeature2
entity = mate.MateEntity(0)
component = entity.ReferenceComponent
before_transform = tuple(component.Transform2.ArrayData)
candidate_faces = []
for body in component.GetModelDoc2.GetBodies2(0, False) or []:
    for face in body.GetFaces() or []:
        surface = face.GetSurface
        if surface.IsCylinder and abs(surface.CylinderParams[6] - 0.004) < 1e-7:
            candidate_faces.append(face)
print('candidates', len(candidate_faces), 'before_error', target.GetErrorCode, flush=True)
face = max(candidate_faces, key=lambda x: x.GetArea)
context_face = component.GetCorresponding(face)
definition = target.GetDefinition
entities = list(definition.EntitiesToMate)
print('old_entities', [x is not None for x in entities], flush=True)
entities[0] = context_face
errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(top.GetTitle, False, errors)
if errors.value:
    raise RuntimeError(f'Could not activate top: {errors.value}')
definition.EntitiesToMate = tuple(entities)
modified = target.ModifyDefinition(definition, top, win32.VARIANT(pythoncom.VT_DISPATCH, None))
print('modified', modified, 'error_after_modify', target.GetErrorCode, flush=True)
top.EditRebuild3()
print('error_after_rebuild', target.GetErrorCode,
      'transform_moved', max(abs(a-b) for a,b in zip(before_transform, component.Transform2.ArrayData)),
      'top_dirty', top.GetSaveFlag, flush=True)

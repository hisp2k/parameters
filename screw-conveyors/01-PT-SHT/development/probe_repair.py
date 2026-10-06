from pathlib import Path
import win32com.client as win32

base = next(Path('outputs').glob('Шнек 1 — параметрическая модель')).resolve()
sw = win32.GetActiveObject('SldWorks.Application')
docs = [doc for doc in (sw.GetDocuments or []) if doc.GetType == 2]
for doc in docs:
    if str(base).casefold() not in doc.GetPathName.casefold():
        continue
    print('ASSEMBLY', Path(doc.GetPathName).name)
    feat = doc.FirstFeature
    while feat:
        if feat.GetTypeName2 == 'MateGroup':
            mate = feat.GetFirstSubFeature
            while mate:
                if mate.Name == 'Концентричный75':
                    print('MATE', mate.Name, mate.GetErrorCode)
                    print('definition type', type(mate.GetDefinition))
                    definition = mate.GetDefinition
                    print('definition attrs', [x for x in dir(definition) if not x.startswith('_')][:60])
                    for attr in ('EntitiesToMate','AccessSelections','MateAlignment','LockRotation'):
                        try: print(attr, getattr(definition, attr))
                        except Exception as exc: print(attr, 'ERROR', exc)
                    specific = mate.GetSpecificFeature2
                    for i in (0, 1):
                        ent = specific.MateEntity(i)
                        comp = ent.ReferenceComponent
                        print(i, comp.Name2, 'ref', ent.Reference, 'type', ent.ReferenceType2,
                              'params', list(ent.EntityParams or []))
                        print('component transform', list(comp.Transform2.ArrayData))
                        part = comp.GetModelDoc2
                        bodies = part.GetBodies2(0, True) if part else []
                        print('bodies', type(bodies), str(bodies)[:100])
                        if isinstance(bodies, (list, tuple)):
                            for body in bodies[:1]:
                                faces = body.GetFaces() or []
                                print('face count', len(faces))
                                n = 0
                                for face in faces:
                                    surf = face.GetSurface
                                    if surf.IsCylinder:
                                        print('cylinder', n, list(surf.CylinderParams), 'box', list(face.GetBox))
                                        n += 1
                                        if n > 8: break
                    raise SystemExit
                mate = mate.GetNextSubFeature
        feat = feat.GetNextFeature

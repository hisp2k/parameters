from pathlib import Path
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
base = next(Path('outputs').glob('Шнек 1 — параметрическая модель')).resolve()
top = next(d for d in (sw.GetDocuments or []) if d.GetType == 2 and
           str(base).casefold() in d.GetPathName.casefold() and
           '20.00.00' in d.GetTitle and '— восстановлено' in d.GetTitle)
feature = top.FirstFeature
while feature:
    if feature.GetTypeName2 == 'MateGroup':
        mate_feature = feature.GetFirstSubFeature
        while mate_feature:
            if mate_feature.Name == 'Концентричный75':
                mate = mate_feature.GetSpecificFeature2
                entity = mate.MateEntity(0)
                comp = entity.ReferenceComponent
                print('mate',mate_feature.Name,'params',entity.EntityParams,flush=True)
                part = comp.GetModelDoc2
                print('part',part.GetPathName,flush=True)
                for body in part.GetBodies2(0, False) or []:
                    for face in body.GetFaces() or []:
                        surface = face.GetSurface
                        if surface.IsCylinder:
                            ctx = comp.GetCorresponding(face)
                            print('local',surface.CylinderParams,'area',face.GetArea,
                                  'box',face.GetBox,flush=True)
                            if ctx:
                                print('context',ctx.GetSurface.CylinderParams,
                                      'area',ctx.GetArea,'box',ctx.GetBox,flush=True)
                definition = mate_feature.GetDefinition
                print('definition',type(definition).__name__,flush=True)
                try:
                    entities = definition.EntitiesToMate
                    print('entities',[(type(x).__name__ if x else None) for x in entities],flush=True)
                except Exception as exc:
                    print('entities error',exc,flush=True)
                raise SystemExit(0)
            mate_feature = mate_feature.GetNextSubFeature
    feature = feature.GetNextFeature

from pathlib import Path
import json
import win32com.client as win32

project = next(Path('outputs').glob('Шнек 1 — параметрическая модель'))
top_path = Path(json.loads((project / 'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly'])
sw = win32.GetActiveObject('SldWorks.Application')
top = sw.GetOpenDocumentByName(str(top_path))
if top is None:
    raise SystemExit('Recovered top assembly is not open')
feature = top.FirstFeature
while feature:
    if feature.GetTypeName2 == 'MateGroup':
        mate_feature = feature.GetFirstSubFeature
        while mate_feature:
            if mate_feature.GetErrorCode == 48:
                mate = mate_feature.GetSpecificFeature2
                print('FEATURE', mate_feature.Name, mate_feature.GetTypeName2)
                for i in (0, 1):
                    entity = mate.MateEntity(i)
                    print('ENTITY', i, 'params', entity.EntityParams,
                          'component', entity.ReferenceComponent.Name2 if entity.ReferenceComponent else None,
                          'ref', type(entity.Reference).__name__ if entity.Reference else None)
                    if i == 0:
                        component = entity.ReferenceComponent
                        part = component.GetModelDoc2
                        print('PART', part.GetPathName)
                        for body in (part.GetBodies2(0, False) or []):
                            for face in (body.GetFaces() or []):
                                surface = face.GetSurface
                                if surface.IsCylinder:
                                    print('CYL', surface.CylinderParams)
                raise SystemExit(0)
            mate_feature = mate_feature.GetNextSubFeature
    feature = feature.GetNextFeature

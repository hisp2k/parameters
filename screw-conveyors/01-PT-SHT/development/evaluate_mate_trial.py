from pathlib import Path
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
path = (Path('work') / 'mate_trial' / 'CAD_восстановленный' / 'Шнек 1 — испытание сопряжений.SLDASM').resolve()
doc = sw.GetOpenDocumentByName(str(path))
print('loaded', doc is not None)
if not doc:
    raise SystemExit
group = doc.FirstFeature
while group:
    if group.GetTypeName2 == 'MateGroup':
        feature = group.GetFirstSubFeature
        errors = []
        names = []
        while feature:
            names.append((feature.Name, feature.GetErrorCode))
            if feature.GetErrorCode == 48:
                errors.append(feature.Name)
            feature = feature.GetNextSubFeature
        print('broken', len(errors), 'last', names[-5:])
        print('target', [x for x in names if x[0] == 'Концентричный75'])
    group = group.GetNextFeature
for component in doc.GetComponents(False) or []:
    if component.Name2 == 'Болт М8х25 DIN 933-1':
        print('bolt transform', component.Transform2.ArrayData)

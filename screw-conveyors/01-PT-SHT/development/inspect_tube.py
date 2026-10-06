from pathlib import Path
from collections import Counter
import json
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
base = Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD'
path = next(base.rglob("PT.SHT.01.21.00.09 'Труба шнека'.SLDPRT")).resolve()
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 1
spec.ReadOnly = True
spec.Silent = True
doc = sw.OpenDoc7(spec)
print('part', doc.GetPathName.encode('unicode_escape').decode())
print('box', doc.GetPartBox(True))
print('features', [(f.Name.encode('unicode_escape').decode(), f.GetTypeName2) for f in []])
try:
    bodies = doc.GetBodies2(0, False) or []
    radii = []
    for body in bodies:
        for face in body.GetFaces() or []:
            surf = face.GetSurface
            if surf.IsCylinder:
                pars = surf.CylinderParams
                radii.append(round(float(pars[6])*1000, 4))
    print('cylinder_radii_mm', Counter(radii))
except Exception as exc:
    print('geometry_error', repr(exc))
feat = doc.FirstFeature
while feat:
    print('feature', feat.Name.encode('unicode_escape').decode(), feat.GetTypeName2)
    feat = feat.GetNextFeature

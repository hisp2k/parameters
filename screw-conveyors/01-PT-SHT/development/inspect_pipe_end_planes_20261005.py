from pathlib import Path
import json,sys
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');support=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
for c in support.GetComponents(True):
    if not any(s in c.Name2 for s in (".25.00.09 '",".25.00.07 '")):continue
    print('PART',c.Name2,flush=True);p=c.GetModelDoc2
    for name in ['Плоскость1','Плоскость2','Плоскость3','Плоскость4']:
        f=p.FeatureByName(name)
        if f:
            print('Plane',name,list(f.GetSpecificFeature2.Transform.ArrayData),flush=True)
    for b in p.GetBodies2(0,True):
        print('Body box',b.GetBodyBox,flush=True)
        for face in b.GetFaces():
            s=face.GetSurface
            if s.IsPlane and face.GetArea*1e6>200:
                print('Face',list(s.PlaneParams),'normal',face.Normal,'area',face.GetArea*1e6,'box',face.GetBox,flush=True)
    boss=p.FeatureByName('Бобышка-Вытянуть1');data=boss.GetDefinition
    print('End conditions/depths',data.GetEndCondition(True),data.GetEndCondition(False),data.GetDepth(True),data.GetDepth(False),flush=True)
d=json.loads((base/'support_pipe_connections_before_20261005.json').read_text(encoding='utf-8'))
for m in d['mates']:
    if not m['suppressed']:print('ACTIVE MATE',m['name'],[(e['component'],e['name']) for e in m['entities']],flush=True)

from pathlib import Path
import json,sys,math
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');support=sw.GetOpenDocumentByName(str(bridge.FILES['support']));assert support
components=[];mates=[]
for c in support.GetComponents(True):
    p=c.GetModelDoc2
    row={'name':c.Name2,'path':c.GetPathName,'fixed':bool(c.IsFixed),'transform':list(c.Transform2.ArrayData),'box':list(p.GetPartBox(True)) if p.GetType==1 else None}
    if any(t in c.Name2 for t in ('Подкос','Стойка','Балка')):
        row['features']=[];f=p.FirstFeature
        while f:
            item={'name':f.Name,'type':f.GetTypeName2,'suppressed':bool(f.IsSuppressed),'error':f.GetErrorCode}
            display=f.GetFirstDisplayDimension
            item['dimensions']=[]
            while display:
                d=display.GetDimension2(0);item['dimensions'].append({'name':d.FullName,'value':d.SystemValue})
                display=f.GetNextDisplayDimension(display)
            row['features'].append(item);f=f.GetNextFeature
        row['planes']=[]
        for b in p.GetBodies2(0,True):
            for face in b.GetFaces():
                s=face.GetSurface
                if s.IsPlane:row['planes'].append({'params':list(s.PlaneParams),'normal':list(face.Normal),'area_mm2':face.GetArea*1e6})
    components.append(row)
f=support.FirstFeature
while f:
    if f.GetTypeName2=='MateGroup':
        m=f.GetFirstSubFeature
        while m:
            mate=m.GetSpecificFeature2
            if mate:
                entities=[]
                for i in range(mate.GetMateEntityCount):
                    entity=mate.MateEntity(i);component=entity.ReferenceComponent
                    ref=entity.Reference
                    try:name=ref.Name
                    except Exception:name=None
                    entities.append({'component':component.Name2 if component else None,'type':entity.ReferenceType2,'name':name,'parameters':list(entity.EntityParams or []),'reference_present':ref is not None})
                mates.append({'name':m.Name,'type':m.GetTypeName2,'suppressed':bool(m.IsSuppressed),'error':m.GetErrorCode,'entities':entities})
            m=m.GetNextSubFeature
    f=f.GetNextFeature
result={'components':components,'mates':mates}
(base/'support_pipe_connections_before_20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for row in components:
    if any(t in row['name'] for t in ('Подкос','Стойка','Балка')):
        print(row['name'],'transform',row['transform'],'box',row['box'],flush=True)
        print('Dimensions:',[(item['name'],item['dimensions']) for item in row['features'] if item['dimensions'] and not item['suppressed']],flush=True)
for row in mates:
    if any('Подкос' in (e['component'] or '') for e in row['entities']):print('BRACE MATE',row,flush=True)

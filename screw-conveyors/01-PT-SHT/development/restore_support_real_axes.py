exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
for m in list(mates(support)):
 if m.Name in ['Расстояние5 — восстановлено','Расстояние6 — восстановлено'] or (m.GetErrorCode==1 and m.GetTypeName2=='MateDistanceDim'):
  support.ClearSelection2(True);m.Select2(False,0);support.Extension.DeleteSelection2(0)
c=next(c for c in support.GetComponents(True) if c.Name2.startswith('PT.SHT.01.01.02.03') and c.Name2.endswith('-1'));part=c.GetModelDoc2;sw.ActivateDoc3(part.GetTitle,False,2,e)
edges=[]
for b in part.GetBodies2(0,True):
 for edge in b.GetEdges():
  curve=edge.GetCurve
  if curve.IsLine:
   p=list(curve.LineParams)
   if abs(p[0]+.05)<1e-7 and abs(p[1]-.003)<1e-7 and abs(p[5])>.99999:edges.append(edge)
print('edges',len(edges),flush=True)
part.ClearSelection2(True);edges[0].Select4(False,part.SelectionManager.CreateSelectData)
if not part.InsertAxis2(True):raise RuntimeError('Edge axis failed')
f=part.FirstFeature;axes=[]
while f:
 if f.GetTypeName2=='RefAxis':axes.append(f)
 f=f.GetNextFeature
axes[-1].Name='Ось кромки пластины — восстановлено';part.Save3(1,e,q)
sw.ActivateDoc3(support.GetTitle,False,2,e)
r=json.loads((base/'mate_diagnostics_20261004.json').read_text(encoding='utf-8'));src=next(a for a in r if 'Опора шнековая' in a['assembly'])
for oldname,compname,planename,axisname,distance in [
 ('Расстояние5','PT.SHT.01.01.02.03  Лапа-1',None,'Ось кромки пластины — восстановлено',.02),
 ('Расстояние6','PT.SHT.01.01.02.03  Лапа-2',None,'Ось кромки пластины — восстановлено',.02),
 ('Расстояние9','PT.SHT.01.01.02.03  Лапа-2',None,'Ось отверстия пластины — восстановлено',.05)]:
 compname=next(c.Name2 for c in support.GetComponents(True) if c.Name2.startswith('PT.SHT.01.01.02.03') and c.Name2.endswith(compname[-2:]))
 old=next((m for m in mates(support) if m.Name==oldname),None)
 if old:
  plane=old.GetDefinition.EntitiesToMate[1].GetSpecificFeature2;old.SetSuppression2(0,1,None)
 else:
  ent=next(a for a in src['errors'] if a['name']==oldname)['entities'][0]
  comp=next(c for c in support.GetComponents(True) if c.Name2==ent['component'])
  p=ent['params'];t=list(comp.Transform2.ArrayData);choices=[]
  for body in comp.GetModelDoc2.GetBodies2(0,True):
   for edge in body.GetEdges():
    curve=edge.GetCurve
    if not curve.IsLine:continue
    line=list(curve.LineParams);n=[sum(line[3+j]*t[j*3+i] for j in range(3)) for i in range(3)];o=[sum(line[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
    v=[o[i]-p[i] for i in range(3)];axial=sum(v[i]*p[3+i] for i in range(3));perp=sum((v[i]-axial*p[3+i])**2 for i in range(3))**.5
    if abs(sum(n[i]*p[3+i] for i in range(3)))>.99999 and perp<1e-6:choices.append(edge)
  if len(choices)!=1:raise RuntimeError('Beam edge ambiguous '+oldname+' '+str(len(choices)))
  plane=comp.GetCorrespondingEntity(choices[0])
 support.ClearSelection2(True);fullname=axisname+'@'+compname+'@'+support.GetTitle.removesuffix('.SLDASM')
 if not support.Extension.SelectByID2(fullname,'AXIS',0.,0.,0.,False,1,w.VARIANT(pythoncom.VT_DISPATCH,None),0):raise RuntimeError('Axis selection')
 axis=support.SelectionManager.GetSelectedObject6(1,1).GetSpecificFeature2
 data=support.CreateMateData(5);data.IsAdvancedMate=False;data.Distance=distance;data.MateAlignment=2;data.FlipDimension=True;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[plane,axis])
 new=support.CreateMate(data);print(oldname,'new',new,'err',new.GetErrorCode if new else None,flush=True)
 if not new or new.GetErrorCode:raise RuntimeError('New mate invalid')
 if old:support.ClearSelection2(True);old.Select2(False,0);support.Extension.DeleteSelection2(0)
 new.Name=oldname+' — восстановлено'
print('supportsave',support.Save3(1,e,q),e.value,q.value,flush=True);doc.ForceRebuild3(False);print('topsave',doc.Save3(1,e,q),e.value,q.value,flush=True)



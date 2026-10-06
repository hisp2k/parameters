exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
c=next(c for c in doc.GetComponents(True) if 'Шнековый вал' in c.Name2);d=c.GetModelDoc2
sw.ActivateDoc3(d.GetTitle,False,2,w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0))
for c in d.GetComponents(True):
 print('COMP',c.Name2,'path',c.GetPathName,'transform',list(c.Transform2.ArrayData),'box',c.GetModelDoc2.GetPartBox(True),flush=True)
for f in mates(d):
 m=f.GetSpecificFeature2
 print('MATE',f.Name,f.GetTypeName2,'error',f.GetErrorCode,flush=True)
 for i in range(m.GetMateEntityCount):
  e=m.MateEntity(i);print(e.ReferenceComponent.Name2,list(e.EntityParams or []),flush=True)
eq=d.GetEquationMgr
for i in range(eq.GetCount):print('EQ',i,eq.Equation(i),flush=True)

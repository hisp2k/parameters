exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(doc.GetTitle,False,2,e)
cap=next(c for c in doc.GetComponents(True) if 'Ограничитель верхний' in c.Name2)
shaft=next(c for c in doc.GetComponents(False) if 'Вал шнека верхний' in c.Name2)
print('fixed',cap.IsFixed,flush=True)
def face(c,axis,value):
 fs=[f for b in c.GetModelDoc2.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsPlane and abs(f.GetBox[axis]-value)<1e-7 and abs(f.GetBox[axis+3]-value)<1e-7]
 assert len(fs)==1,(c.Name2,len(fs));return c.GetCorrespondingEntity(fs[0])
fs=[face(shaft,2,-.331),face(cap,1,0.)]
data=doc.CreateMateData(0);data.MateAlignment=1;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,fs)
new=doc.CreateMate(data);assert new and not new.GetErrorCode
new.Name='Ограничитель верхний — посадка на торец вала'
doc.ForceRebuild3(False);errors=[(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode]
print('errors',errors,'position',list(cap.Transform2.ArrayData[9:12]),flush=True);assert not errors
print('saved',doc.Save3(1,e,q),e.value,q.value,flush=True)

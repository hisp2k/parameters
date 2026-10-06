exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil,math
cs=[(c.Name2,c) for c in doc.GetComponents(False)]
a=next(c for n,c in cs if 'Обойма верхняя' in n and 'Фланец обоймы' in n);b=next(c for n,c in cs if 'Труба в сборе' in n and 'Фланец трубы шнека' in n and n.endswith('-2'))
def hole(c):
 options=[];t=list(c.Transform2.ArrayData)
 for body in c.GetModelDoc2.GetBodies2(0,True):
  for f in body.GetFaces():
   sf=f.GetSurface
   if sf.IsCylinder:
    v=list(sf.CylinderParams)
    if abs(v[6]-.0044)<1e-7:
     world=[sum(v[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)];options.append((world[0],f))
 assert len(options)==8
 return c.GetCorrespondingEntity(max(options,key=lambda x:x[0])[1])
backup=base/'snapshots/20261004-before-upper-clocking';backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/path.name)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(doc.GetTitle,False,2,e)
data=doc.CreateMateData(1);data.MateAlignment=0;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[hole(a),hole(b)]);new=doc.CreateMate(data);assert new,new
print('new mate',new.GetErrorCode,flush=True);new.Name='Верхняя обойма — совпадение крепёжных отверстий';doc.ForceRebuild3(False);errs=[(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode];print('errors',errs,flush=True);assert not errs;assert doc.Save3(1,e,q);print('saved clock alignment',flush=True)

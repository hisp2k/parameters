from pathlib import Path
import json,sys,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)

def activate(d):sw.ActivateDoc3(d.GetPathName,False,2,e);assert not e.value

def cylinder(c,diam):
 fs=[f for b in c.GetModelDoc2.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder and abs(f.GetSurface.CylinderParams[6]*2000-diam)<1e-6]
 assert fs,c.Name2
 f=max(fs,key=lambda f:f.GetArea);t=list(c.Transform2.ArrayData);p=list(f.GetSurface.CylinderParams);axis=[sum(p[3+j]*t[j*3+i] for j in range(3)) for i in range(3)]
 return c.GetCorrespondingEntity(f),axis

def concentric(d,c1,c2,diam1,diam2,name):
 activate(d);f1,a1=cylinder(c1,diam1);f2,a2=cylinder(c2,diam2)
 data=d.CreateMateData(1);data.MateAlignment=0 if sum(a1[i]*a2[i] for i in range(3))>0 else 1;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[f1,f2])
 mate=d.CreateMate(data);assert mate,name
 mate.Name=name;print('Added',name,'error',mate.GetErrorCode,flush=True)
 return mate
try:
 path=json.loads((base/'pin_joint_trial_20261005.json').read_text(encoding='utf-8'))['root'];root=sw.GetOpenDocumentByName(path);assert root
 topcs=list(root.GetComponents(False));support=next(c.GetModelDoc2 for c in root.GetComponents(True) if 'Опора шнековая' in c.Name2)
 bush=next(c for c in topcs if "'Втулка'" in c.Name2 and c.Name2.endswith('-2'))
 activate(root)
 for name in ('Угол1','Совпадение111'):
  old_frame=root.FeatureByName(name);assert old_frame;assert old_frame.SetSuppression2(0,1,None)
 existing=root.FeatureByName('Втулка 2 — ухо 3 — соосность')
 if not existing:
  ear=next(c for c in topcs if "'Ухо'" in c.Name2 and c.Name2.endswith('-3'))
  concentric(root,bush,ear,18,10.8,'Втулка 2 — ухо 3 — соосность')
 ear4=next(c for c in topcs if "'Ухо'" in c.Name2 and c.Name2.endswith('-4'))
 def seating_face(c,x):
  choices=[];t=list(c.Transform2.ArrayData)
  for b in c.GetModelDoc2.GetBodies2(0,True):
   for f in b.GetFaces():
    surface=f.GetSurface
    if not surface.IsPlane:continue
    v=list(surface.PlaneParams);point=[sum(v[3+j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
    n=list(f.Normal);normal=[sum(n[j]*t[j*3+i] for j in range(3)) for i in range(3)]
    if abs(point[0]-x)<1e-6 and abs(normal[0])>.9999:choices.append((f.GetArea,f,normal))
  assert choices,(c.Name2,x)
  _,f,normal=max(choices,key=lambda v:v[0]);return c.GetCorrespondingEntity(f),normal
 f1,n1=seating_face(bush,.030);f2,n2=seating_face(ear4,.030)
 data=root.CreateMateData(0);data.MateAlignment=0 if sum(n1[i]*n2[i] for i in range(3))>0 else 1
 data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[f1,f2]);seat=root.CreateMate(data);assert seat
 seat.Name='Втулка 2 — ухо 4 — торцевая посадка';print('Added seat',seat.GetErrorCode,flush=True)
 activate(support);old=support.FeatureByName('Совпадение17');assert old;assert old.SetSuppression2(0,1,None)
 cs=list(support.GetComponents(True));bush=next(c for c in cs if "'Втулка'" in c.Name2 and c.Name2.endswith('-2'))
 for side,match in [(1,".25.00.09 '")]:
  brace=next(c for c in cs if match in c.Name2)
  concentric(support,brace,bush,18,18,'Подкос '+str(side)+' — втулка 2 — соосность')
 print('Support rebuilt',support.ForceRebuild3(False),flush=True);activate(root);print('Root rebuilt',root.ForceRebuild3(False),flush=True)
 issues=bridge.model_issues(sw,root);print('Issues',issues,flush=True);ints=bridge.interference_issues(root);print('Intersections',ints[:10],flush=True)
 proof={'root':path,'issues':issues,'interferences':ints};(base/'pin_joint_explicit_mates_trial_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
 if issues==(0,0,[]) and not ints:
  activate(support);support.ClearSelection2(True);assert old.Select2(False,0);assert support.Extension.DeleteSelection2(0)
  activate(root)
  for name in ('Угол1','Совпадение111'):
   f=root.FeatureByName(name);root.ClearSelection2(True);assert f.Select2(False,0);assert root.Extension.DeleteSelection2(0)
  assert root.Save3(13,e,q) and not e.value
finally:sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,e);sw.CommandInProgress=prev

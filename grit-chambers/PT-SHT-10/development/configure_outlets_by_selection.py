from pathlib import Path
import json,win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
sw=w.Dispatch('SldWorks.Application');a=sw.ActiveDoc;uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
f=typed(p.GetFeatures(),'IProjectFeatures');assert len(f.GetFeatures2(True,0) or [])==1
app.SetSilent();log=[]
try:
 for comp,axis,coord,fc,par,val in [('CFD_outlet_flange_lid-2',2,0.,10,3,101325.),('CFD_bottom_flange_lid-2',1,.005,6,18,.1/3600)]:
  c=next(c for c in a.GetComponents(False) if c.Name2==comp);faces=c.GetBody.GetFaces()
  for i,face in enumerate(faces):print(comp,'FACE',i,face.GetBox,flush=True)
  face=next(face for face in faces if abs(face.GetBox[axis]-coord)<1e-8 and abs(face.GetBox[axis+3]-coord)<1e-8)
  a.ClearSelection2(True);assert face.Select2(False,0)
  assert a.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2==comp
  b=uip.CreateTemplateBoundaryCondition();b.FCType=fc
  print('REFS',uip.UpdateFeatureTopolReferenciesFromSelection(0,b),b.GetReferencesNames(),flush=True)
  assert b.ApplyUIChanges(uip,False,True)
  bc=typed(next(x for x in f.GetFeatures2(True,0) if x.GetUUID()==b.UUID_),'IBoundaryCondition')
  bc.put_FCType(fc);bc.GetParameter(par).SetValue(val)
  ok=p.Rebuild(False,True,True,False,False,False);err=p.GetLastRebuildError();print('REBUILD',ok,err,flush=True)
  if not ok or err:raise RuntimeError(err)
 for raw in f.GetFeatures2(True,0):
  bc=typed(raw,'IBoundaryCondition');fc=bc.get_FCType();par=3 if fc==10 else 18
  row={'name':bc.GetName(),'type':fc,'value_SI':bc.GetParameter(par).GetValue(0.),'references':bc.GetTopologicalReferencesUUIDsAndNames(None,None)};log.append(row);print('VALID',json.dumps(row,ensure_ascii=False),flush=True)
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('SAVE',a.Save3(1,e,v),e.value,v.value,flush=True)
finally:
 app.ResetSilent();Path('work/valid_boundary_conditions.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')

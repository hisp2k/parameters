from pathlib import Path
import uuid,json,win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
sw=w.Dispatch('SldWorks.Application');cad=sw.ActiveDoc
assert 'pt-sht-10-demo' in cad.GetPathName
assert p.GetName()=='PT-SHT-10-demo-Q10-sealed'
api=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc
f=typed(p.GetFeatures(),'IProjectFeatures');g=typed(p.GetGeneralSettings(),'IGeneralSettings')
log=[];app.SetSilent()
try:
 for old in f.GetFeatures2(True,0) or []:
  print('existing',old.GetName(),flush=True)
  raise RuntimeError('Existing BC requires review before changes')
 ambient=typed(g.GetAmbientParameters(),'IAmbientParameters')
 print('ambient P',ambient.GetParameter(0).GetValue(0.),flush=True)
 for name,comp,face,pt,fc,param,value in [
  ('Inlet Q=10 m3h','CFD_inlet_lid-2',2,(.2515,.7195,.329),1,18,10/3600),
  ('Main outlet p=0 Pa gauge','CFD_outlet_flange_lid-2',2,(0.,.458,.353),10,3,101325.),
  ('Bottom outlet Q=0.10 m3h','CFD_bottom_flange_lid-2',1,(0.,.004,0.),6,18,.1/3600)]:
  uid=str(uuid.uuid4());attr=api.CreateAttributeOnComponentSolidBodyTopology(comp,0,2,*pt,uid)
  print('face attribute',name,attr,uid,flush=True)
  if not attr:raise RuntimeError('Face attribute not created')
  b=typed(f.CreateFeature(0),'IBoundaryCondition');b.SetName(name);b.put_FCType(fc)
  b.GetParameter(param).SetValue(value)
  b.AddTopologicalReferenceUUIDAndName(uid,comp+'/Бобышка-Вытянуть1//Поверхность<'+str(face)+'>')
  print('add',name,f.AddUpdateFeature(p,b),flush=True)
  ok=p.Rebuild(True,True,True,False,False,False);err=p.GetLastRebuildError()
  row={'name':name,'type':fc,'parameter':param,'value_SI':b.GetParameter(param).GetValue(0.),'rebuilt':ok,'error':err,'uuid':uid};log.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  if not ok or err:raise RuntimeError('Flow rejected BC: '+str(err))
 print('ALL THREE BC VALID',flush=True)
finally:
 app.ResetSilent()
 Path('work/repeated_flow_bc_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')

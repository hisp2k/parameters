import uuid
import win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
sw=w.Dispatch('SldWorks.Application');d=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc
uid=str(uuid.uuid4());nm='CFD_inlet_lid-2/Бобышка-Вытянуть1//Поверхность<2>'
print('attr',d.CreateAttributeOnComponentSolidBodyTopology('CFD_inlet_lid-2',0,2,.2515,.7195,.329,uid),uid,flush=True)
f=typed(p.GetFeatures(),'IProjectFeatures');b=typed(f.CreateFeature(0),'IBoundaryCondition')
b.put_FCType(1);b.GetParameter(18).SetValue(10/3600);b.AddTopologicalReferenceUUIDAndName(uid,nm)
print('add start',flush=True)
print('add',f.AddUpdateFeature(p,b),flush=True)
print('rebuild',p.Rebuild(True,True,True,False,False,False),flush=True)
print('error',p.GetLastRebuildError(),flush=True)

exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
import win32com.client as w
sw=w.Dispatch('SldWorks.Application');a=sw.ActiveDoc
f=typed(p.GetFeatures(),'IProjectFeatures')
for old in f.GetFeatures2(True,0) or []:print('remove failed BC',f.RemoveFeature(old.GetUUID()),flush=True)
c=next(c for c in a.GetComponents(False) if c.Name2=='CFD_inlet_lid-2')
faces=c.GetBody.GetFaces()
for i,face in enumerate(faces):print('FACE',i,face.GetBox,flush=True)
face=next(face for face in faces if abs(face.GetBox[2])<1e-8 and abs(face.GetBox[5])<1e-8)
a.ClearSelection2(True);print('SELECT',face.Select2(False,0),flush=True)
print('SELECTED COMP',a.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2,flush=True)
uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
b=uip.CreateTemplateBoundaryCondition();b.FCType=1;b.Name_='Inlet Q10 via selected face'
print('REFS',uip.UpdateFeatureTopolReferenciesFromSelection(0,b),b.GetReferencesNames(),flush=True)
print('TYPE',b.FCType,flush=True)
app.SetSilent()
try:
 print('APPLY',b.ApplyUIChanges(uip,False,False),flush=True)
 for raw in f.GetFeatures2(True,0) or []:
  bc=typed(raw,'IBoundaryCondition');bc.put_FCType(1);bc.GetParameter(18).SetValue(10/3600)
 print('REBUILD',p.Rebuild(False,True,True,False,False,False),p.GetLastRebuildError(),flush=True)
finally:app.ResetSilent()

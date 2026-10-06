from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application')
p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p));err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
s.ActivateDoc3(d.GetTitle,False,0,err)
comp=next(c for c in d.GetComponents(False) or [] if c.Name2=='CFD_крышка_боковая-1')
face=(comp.GetBody.GetFaces() or [])[2]
d.ClearSelection2(True)
print('face select',face.Select2(False,0),'sel comp',d.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2,flush=True)
proj=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
print('project',proj.ProjectName,flush=True)
b=proj.CreateTemplateBoundaryCondition();b.Name_='CFD Inlet 10 m3h';b.FCType=1
print('assign topol',proj.UpdateFeatureTopolReferenciesFromSelection(0,b),b.GetReferencesNames(),flush=True)
ok=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_BOOL,False)
try:
 out=b.ApplyUIChanges(b,False,False)
 print('apply',out,'ok',ok.value,flush=True)
except Exception as e:print('apply ERR',repr(e),flush=True)

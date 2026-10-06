import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
a=s.GetOpenDocumentByName(str(p));print('active',s.ActiveDoc.GetPathName,'assembly',a.GetPathName)
for nm,index in [('CFD_inlet_flange_lid-1',2),('CFD_outlet_flange_lid-1',2),('CFD_bottom_flange_lid-1',1)]:
 c=next(c for c in a.GetComponents(False) or [] if c.Name2==nm)
 face=(c.GetBody.GetFaces() or [])[index]
 a.ClearSelection2(True);print(nm,'select',face.Select2(False,0),'comp',a.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2)
 proj=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
 b=proj.CreateTemplateBoundaryCondition()
 print(' topol',proj.UpdateFeatureTopolReferenciesFromSelection(0,b),b.GetReferencesNames())

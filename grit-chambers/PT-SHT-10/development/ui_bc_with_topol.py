from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application');p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'));a=s.GetOpenDocumentByName(str(p))
c=next(c for c in a.GetComponents(False) or [] if c.Name2=='CFD_inlet_flange_lid-2')
face=(c.GetBody.GetFaces() or [])[2];a.ClearSelection2(True);print('select',face.Select2(False,0))
proj=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
b=proj.CreateTemplateBoundaryCondition();b.FCType=1;b.Name_='CFD inlet 10'
print('topol',proj.UpdateFeatureTopolReferenciesFromSelection(0,b),b.GetReferencesNames())
for k in [18,16,17,3]:
 try:
  q=b.GetParameter(k,'');print('param',k,q,q.value if q else None)
  if k==18 and q:q.value=10/3600;print('set',q.value)
 except Exception as e:print('ERR',k,repr(e))
for first in [None]:
 try:print('apply',b.ApplyUIChanges(first,False,False))
 except Exception as e:print('apply ERR',repr(e))

from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p));e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);s.ActivateDoc3(d.GetTitle,False,0,e)
comp=next(c for c in d.GetComponents(False) or [] if 'CFD_крышка_нижняя-1' in c.Name2)
f=(comp.GetBody.GetFaces() or [])[1]
d.ClearSelection2(True)
for m,args in [('Select4',(False,None)),('Select2',(False,0))]:
 try:
  x=getattr(f,m)(*args);print(m,x)
  if x:break
 except Exception as z:print(m,'ERR',repr(z))
print('count',d.SelectionManager.GetSelectedObjectCount2(-1))
try:print('component',d.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2)
except Exception as z:print('component ERR',repr(z))

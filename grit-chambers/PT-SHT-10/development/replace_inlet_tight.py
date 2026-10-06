from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');a=s.ActiveDoc
for c in a.GetComponents(False) or []:
 if c.Name2=='CFD_inlet_flange_lid-3':print('suppress',c.SetSuppression2(0),flush=True)
path=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_inlet_lid.SLDPRT'
c=a.AddComponent4(str(path),'',.2515,.7195,.3315)
print('added',c.Name2,list(c.GetBox(False,False)),flush=True)
print('rebuild CAD',a.ForceRebuild3(False),flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,e,v),e.value,v.value,flush=True)

from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель';p=next(base.glob('*Бункер в сборе.SLDASM'))
a=s.GetOpenDocumentByName(str(p));e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);s.ActivateDoc3(a.GetTitle,False,0,e)
for c in a.GetComponents(False) or []:
 if c.Name2.startswith(('CFD_inlet_lid-','CFD_outlet_lid-','CFD_bottom_lid-')):
  print('suppress',c.Name2,c.SetSuppression2(0),c.GetSuppression,flush=True)
for file,x,y,z in [('CFD_inlet_flange_lid.SLDPRT',0.2515,0.7195,0.3365),('CFD_outlet_flange_lid.SLDPRT',0.0,0.458,0.3565),('CFD_bottom_flange_lid.SLDPRT',0.0,0.0005,0.0)]:
 c=a.AddComponent4(str(base/file),'',x,y,z)
 print('insert',c.Name2,list(c.GetBox(False,False)),flush=True)
print('rebuild',a.ForceRebuild3(False),flush=True)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warn=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,err,warn),err.value,warn.value,flush=True)

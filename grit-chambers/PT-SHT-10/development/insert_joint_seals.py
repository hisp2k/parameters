from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель';a=s.GetOpenDocumentByName(str(next(base.glob('*Бункер в сборе.SLDASM'))))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);s.ActivateDoc3(a.GetTitle,False,0,e)
for file,x,y,z in [('CFD_inlet_joint_seal_v2.SLDPRT',0.2515,0.7195,0.3255),('CFD_outlet_joint_seal_v2.SLDPRT',0,0.458,0.345),('CFD_bottom_joint_seal_v2.SLDPRT',0,0.0055,0)]:
 c=a.AddComponent4(str(base/file),'',x,y,z)
 print('insert',c.Name2,list(c.GetBox(False,False)),flush=True)
print('rebuild',a.ForceRebuild3(False),flush=True)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warn=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,err,warn),err.value,warn.value,flush=True)

from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application')
p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p));print('existing',bool(d),flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
a=s.ActivateDoc3(d.GetTitle,False,0,e)
print('active',a.GetPathName if a else None,'error',e.value,flush=True)
lid=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_крышка_боковая.SLDPRT'
c=a.AddComponent4(str(lid),'',0.2515,0.7195,0.3365)
print('added',bool(c),c.Name2 if c else None,flush=True)
if c:
 print('initial box',c.GetBox(False,False),flush=True)
 mat=s.GetMathUtility
 print('mat',mat,flush=True)
 trans=mat.CreateTransform((1,0,0,0,1,0,0,0,1,0.2515,0.7195,0.334,1,0,0,0))
 print('transform',bool(trans),flush=True)
 c.Transform2=trans
 print('final box',c.GetBox(False,False),flush=True)
 print('rebuild',a.ForceRebuild3(False),flush=True)
 print('save',a.Save3(1,e,e),flush=True)

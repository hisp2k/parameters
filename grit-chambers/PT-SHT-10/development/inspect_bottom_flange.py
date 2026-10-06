from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');path=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Фланец присоединительный.SLDPRT'))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);d=s.OpenDoc6(str(path),1,64,'',e,v)
print(path.name,'box',d.GetPartBox(True))
for body in d.GetBodies2(0,False) or []:
 for face in body.GetFaces() or []:
  sf=face.GetSurface
  if sf.IsCylinder:
   q=sf.CylinderParams
   if q[6]>0.04:print('r',q[6],'axis',q[3:6],'box',face.GetBox)

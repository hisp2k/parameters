from pathlib import Path
import win32com.client as w,pythoncom
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'
for pattern in ['Фланец 50*.SLDPRT','Фланец 65*.SLDPRT','*Труба входная.SLDPRT','*Труба внешняя.SLDPRT']:
 path=next(base.glob(pattern))
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 d=s.OpenDoc6(str(path),1,64,'',e,v)
 print('\n',path.name,'box',d.GetPartBox(True))
 for body in d.GetBodies2(0,False) or []:
  for face in body.GetFaces() or []:
   surf=face.GetSurface
   if surf.IsCylinder:
    q=surf.CylinderParams
    if q[6]>0.02: print(' cylinder r',round(q[6],6),'axis',tuple(round(v,5) for v in q[3:6]),'box',face.GetBox)

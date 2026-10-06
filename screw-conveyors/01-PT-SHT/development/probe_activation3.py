from pathlib import Path
import sys,pythoncom,win32com.client as w
b=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(b));import bridge
sw=w.GetActiveObject('SldWorks.Application');d=sw.GetOpenDocumentByName(str(bridge.FILES['tube']));print('target',d.GetTitle,d.GetPathName,flush=True)
for name in [d.GetTitle,str(bridge.FILES['tube'])]:
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);a=sw.ActivateDoc3(name,False,2,e);print('activated',name,'error',e.value,'return',a.GetPathName if a else None,'active',sw.ActiveDoc.GetPathName,flush=True)

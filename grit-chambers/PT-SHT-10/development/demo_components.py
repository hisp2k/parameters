exec(open('work/demo_model_from_rot.py',encoding='utf-8').read().split("while True:")[0])
from pathlib import Path
r=pythoncom.GetRunningObjectTable();e=r.EnumRunning();c=pythoncom.CreateBindCtx(0)
while True:
 x=e.Next(1)
 if not x:raise RuntimeError('missing assembly')
 s=x[0].GetDisplayName(c,None)
 if s.lower().endswith('бункер в сборе.sldasm') and 'pt-sht-10-demo' in s.lower():
  doc=w.Dispatch(r.GetObject(x[0]).QueryInterface(pythoncom.IID_IDispatch));break
for comp in doc.GetComponents(False) or []:
 name=comp.Name2
 if any(v in name for v in ['Труба входная','Труба внешняя','Труба внутренняя','Фланец присоединительный','Отвод','Конус','Цилиндр']):
  print(name)
  print(' box',list(comp.GetBox(False,False)))
  print(' xform',list(comp.Transform2.ArrayData))

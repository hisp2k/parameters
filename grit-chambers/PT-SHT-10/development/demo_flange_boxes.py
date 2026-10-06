import win32com.client as w
s=w.Dispatch('SldWorks.Application')
from pathlib import Path
p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p))
print('doc',bool(d),d.GetPathName if d else None)
for comp in d.GetComponents(False) or []:
 n=comp.Name2
 if any(v in n for v in ['Фланец 50','Фланец 65','Фланец присоединительный','Отвод','Труба входная','Труба внешняя','Штуцер']):
  print(n,'BOX',list(comp.GetBox(False,False)))

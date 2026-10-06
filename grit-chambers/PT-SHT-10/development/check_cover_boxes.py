import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');a=s.GetOpenDocumentByName(str(next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))))
for c in a.GetComponents(False) or []:
 n=c.Name2
 if any(k in n for k in ['Крышка','Прокладка','Цилиндр внешний','Конус-1','Отвод-1','Обвязка']):
  try:box=list(c.GetBox(False,False))
  except:box=[]
  print(n,'state',c.GetSuppression,'box',box)

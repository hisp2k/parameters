import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');a=s.GetOpenDocumentByName(str(next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))))
for c in a.GetComponents(False) or []:
 try:b=list(c.GetBox(False,False))
 except:continue
 if b[4]>=0.832 and b[1]<0.84 and (max(abs(b[0]),abs(b[3]),abs(b[2]),abs(b[5]))>0.29):print(c.Name2,b)

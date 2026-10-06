from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application')
p=str((Path.cwd()/'work'/'pt-sht-10-210l'/'Модель'/'PT-SHT-10-210L.SLDASM').resolve())
d=s.GetOpenDocumentByName(p)
root=str((Path.cwd()/'work'/'pt-sht-10-210l').resolve()).lower()
rows=[]
for c in d.GetComponents(False) or []:
 if c.GetSuppression==0:continue
 cp=c.GetPathName
 if cp and not cp.lower().startswith(root):rows.append((c.Name2,cp))
print('EXTERNAL',len(rows))
for x in rows:print(x)

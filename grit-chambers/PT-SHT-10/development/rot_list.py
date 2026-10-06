import pythoncom
r=pythoncom.GetRunningObjectTable();e=r.EnumRunning();c=pythoncom.CreateBindCtx(0)
while True:
 x=e.Next(1)
 if not x:break
 try:s=x[0].GetDisplayName(c,None)
 except:continue
 if 'PT.SHT' in s or 'SldWorks' in s or '36084' in s:print(s)

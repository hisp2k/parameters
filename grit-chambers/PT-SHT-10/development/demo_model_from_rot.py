import pythoncom,win32com.client as w
r=pythoncom.GetRunningObjectTable();e=r.EnumRunning();c=pythoncom.CreateBindCtx(0)
while True:
 x=e.Next(1)
 if not x:break
 try:s=x[0].GetDisplayName(c,None)
 except:continue
 if s.lower().endswith('бункер в сборе.sldasm') and 'pt-sht-10-demo' in s.lower():
  o=w.Dispatch(r.GetObject(x[0]).QueryInterface(pythoncom.IID_IDispatch))
  print('found',s,'path',o.GetPathName,'title',o.GetTitle)
  try:print('app',o.GetSwApp().RevisionNumber)
  except Exception as z:print('app err',repr(z))
  break

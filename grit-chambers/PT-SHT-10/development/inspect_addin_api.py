import win32com.client as w
s=w.Dispatch('SldWorks.Application');o=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
for m in ['GetAPI','GetNGPInterface']:
 try:
  x=getattr(o,m)();print(m,x)
  if x:print(' type',x._oleobj_.GetTypeInfo().GetDocumentation(-1))
 except Exception as e:print(m,'ERR',repr(e))

import win32com.client as w
s=w.Dispatch('SldWorks.Application');a=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
try:
 b=a.CreateTemplateBoundaryCondition()
 print('bc',b,'type',b._oleobj_.GetTypeInfo().GetDocumentation(-1) if b else None)
 for m in ['Name','FCType','UUID']:
  try:print(m,getattr(b,m))
  except Exception as e:print(m,'ERR',repr(e))
except Exception as e:print('ERR',repr(e))

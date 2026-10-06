import win32com.client as w
s=w.Dispatch('SldWorks.Application');p=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
for t in [0,1,6,10]:
 b=p.CreateTemplateBoundaryCondition();b.FCType=t
 print('fctype',t)
 for k in range(0,25):
  try:
   q=b.GetParameter(k,'')
   if q:print(k,q.value)
  except:pass

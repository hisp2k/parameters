import win32com.client as w
s=w.Dispatch('SldWorks.Application'); d=s.ActiveDoc
print('active',d.GetTitle)
f=d.FirstFeature
while f:
 print('feature',f.Name,f.GetTypeName2)
 f=f.GetNextFeature

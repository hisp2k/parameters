import pythoncom,win32com.client as w
pythoncom.CoInitialize()
s=w.Dispatch('SldWorks.Application')
print('active before',s.ActiveDoc.GetTitle)
t=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot'
d=s.NewDocument(t,0,0,0)
print('created',bool(d),'title',d.GetTitle if d else None)
f=d.FirstFeature
while f:
 print('feature',f.Name,f.GetTypeName2)
 f=f.GetNextFeature()

import win32com.client as w
s=w.Dispatch('SldWorks.Application');d=s.NewDocument(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot',0,0,0)
print('doc',d.GetTitle,'active',s.ActiveDoc.GetTitle)
d.ClearSelection2(True)
f=d.FirstFeature
while f and f.Name!='Сверху':f=f.GetNextFeature
print('select2',f.Select2(False,0))
print('selectbyid',d.Extension.SelectByID2('Сверху','PLANE',0,0,0,False,0,None,0))
print('selected',d.SelectionManager.GetSelectedObjectCount2(-1))

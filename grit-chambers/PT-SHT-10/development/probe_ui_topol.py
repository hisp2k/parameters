import win32com.client as w
s=w.Dispatch('SldWorks.Application');proj=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
print('proj',proj.ProjectName)
b=proj.CreateTemplateBoundaryCondition()
print('new',b.Name_,b.FCType)
for k in [0,1,2,3]:
 try:
  print('refmode',k,'result',proj.UpdateFeatureTopolReferenciesFromSelection(k,b),'names',b.GetReferencesNames())
  b.ClearAllTopolReferences()
 except Exception as e:print('refmode',k,'ERR',repr(e))

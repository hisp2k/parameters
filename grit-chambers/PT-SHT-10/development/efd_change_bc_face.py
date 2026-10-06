exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures');b=typed(f.GetFeatures2(True,0)[0],'IBoundaryCondition')
print('before',b.GetTopologicalReferencesUUIDsAndNames(None,None))
try:
 b.ClearAllTopolReferences();print('cleared',b.GetTopologicalReferencesUUIDsAndNames(None,None))
 b.AddTopologicalReferenceUUIDAndName('','CFD_inlet_lid-1/Бобышка-Вытянуть1//Поверхность<1>')
 print('after',b.GetTopologicalReferencesUUIDsAndNames(None,None))
 print('rebuild',p.Rebuild(False,False,True,False,False,False),'last',p.GetLastRebuildError())
except Exception as e:print('ERR',repr(e))

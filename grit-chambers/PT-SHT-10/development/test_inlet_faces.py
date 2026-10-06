exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures');b=typed(f.GetFeatures2(True,0)[0],'IBoundaryCondition')
for face in [1,2]:
 name=f'CFD_inlet_flange_lid-3/Бобышка-Вытянуть1//Поверхность<{face}>'
 b.ClearAllTopolReferences();b.AddTopologicalReferenceUUIDAndName('',name)
 print('face',face,'rebuild',p.Rebuild(True,True,True,False,False,False),flush=True)
 print('error',p.GetLastRebuildError(),flush=True)

exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures');ex=typed(p.GetComponentExplorer(),'IComponentExplorer')
for b in f.GetFeatures2(True,0) or []:
 b=typed(b,'IBoundaryCondition');print('BC',b.GetName(),b.GetTopologicalReferencesUUIDsAndNames(None,None),flush=True)
refs=['CFD_inlet_lid-2/Бобышка-Вытянуть1//Поверхность<2>','CFD_inlet_lid-2','CFD_cylinder_welded-1','CFD_cone_welded-1','CFD_top_cover_sealed-1','CFD_bottom_pipe_extended-1']
for ref in refs:
 try:
  result=p.GetEntity(ref,None,None);print('ENTITY',ref,result,flush=True)
  if result and len(result)>1 and result[-1]:
   ent=typed(result[-1],'ICADEntity');print(' type',ent.GetType(),'disabled',ex.IsDisabledBodyOrComponent(ent,0,False),flush=True)
   print('topology',ent.GetAsTopolObject(),flush=True)
 except Exception as err:print('ERR',repr(err),flush=True)
